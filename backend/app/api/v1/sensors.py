import hmac
from datetime import datetime, timedelta, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.platform import run_analysis
from app.core.config import get_settings
from app.core.security import AuthenticatedUser, require_roles
from app.db.session import get_db_session
from app.models import EndpointSensor, SensorEventReceipt, UserRole
from app.schemas.platform import AnalysisRunRequest
from app.schemas.sensors import (
    EndpointSensorRead,
    SensorIngestRequest,
    SensorIngestResponse,
    SensorServiceStatus,
)

router = APIRouter(prefix="/sensors", tags=["endpoint sensors"])
analyst_or_admin = require_roles(UserRole.analyst, UserRole.administrator)
sensor_actor = AuthenticatedUser(
    id=UUID(int=0),
    username="endpoint-sensor",
    full_name="Local Endpoint Sensor",
    role=UserRole.analyst,
    active=True,
)


def require_sensor_token(
    x_sensor_token: Annotated[str | None, Header()] = None,
) -> None:
    configured = get_settings().sensor_ingest_token
    if configured is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Endpoint sensor ingestion is not configured",
        )
    supplied = x_sensor_token or ""
    if not hmac.compare_digest(supplied.encode(), configured.encode()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sensor authentication failed",
            headers={"WWW-Authenticate": "Sensor"},
        )


def sensor_is_online(last_seen_at: datetime, now: datetime | None = None) -> bool:
    reference = now or datetime.now(timezone.utc)
    return reference - last_seen_at <= timedelta(seconds=get_settings().sensor_offline_seconds)


def sensor_read(sensor: EndpointSensor, now: datetime | None = None) -> EndpointSensorRead:
    return EndpointSensorRead(
        id=sensor.id,
        sensor_id=sensor.sensor_id,
        hostname=sensor.hostname,
        operating_system=sensor.operating_system,
        agent_version=sensor.agent_version,
        ip_addresses=sensor.ip_addresses,
        capabilities=sensor.capabilities,
        last_seen_at=sensor.last_seen_at,
        last_event_at=sensor.last_event_at,
        status="online" if sensor_is_online(sensor.last_seen_at, now) else "offline",
    )


@router.get("", response_model=list[EndpointSensorRead])
async def list_sensors(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> list[EndpointSensorRead]:
    sensors = list(
        (
            await session.scalars(
                select(EndpointSensor).order_by(EndpointSensor.last_seen_at.desc())
            )
        ).all()
    )
    now = datetime.now(timezone.utc)
    return [sensor_read(sensor, now) for sensor in sensors]


@router.get("/status", response_model=SensorServiceStatus)
async def sensor_service_status(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> SensorServiceStatus:
    sensors = list((await session.scalars(select(EndpointSensor))).all())
    now = datetime.now(timezone.utc)
    return SensorServiceStatus(
        ingest_configured=get_settings().sensor_ingest_token is not None,
        sensors_total=len(sensors),
        sensors_online=sum(sensor_is_online(sensor.last_seen_at, now) for sensor in sensors),
    )


@router.post(
    "/ingest",
    response_model=SensorIngestResponse,
    dependencies=[Depends(require_sensor_token)],
)
async def ingest_sensor_batch(
    payload: SensorIngestRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    request: Request,
) -> SensorIngestResponse:
    received_at = datetime.now(timezone.utc)
    sensor = await session.scalar(
        select(EndpointSensor).where(EndpointSensor.sensor_id == payload.sensor_id)
    )
    if sensor is None:
        sensor = EndpointSensor(
            sensor_id=payload.sensor_id,
            hostname=payload.hostname,
            operating_system=payload.operating_system,
            agent_version=payload.agent_version,
            ip_addresses=payload.ip_addresses,
            capabilities=payload.capabilities,
            last_seen_at=received_at,
        )
        session.add(sensor)
    else:
        sensor.hostname = payload.hostname
        sensor.operating_system = payload.operating_system
        sensor.agent_version = payload.agent_version
        sensor.ip_addresses = payload.ip_addresses
        sensor.capabilities = payload.capabilities
        sensor.last_seen_at = received_at
    await session.flush()

    event_keys = [item.event_key for item in payload.events]
    received_keys: set[str] = set()
    if event_keys:
        received_keys = set(
            (
                await session.scalars(
                    select(SensorEventReceipt.event_key).where(
                        SensorEventReceipt.sensor_id == payload.sensor_id,
                        SensorEventReceipt.event_key.in_(event_keys),
                    )
                )
            ).all()
        )
    new_items = [item for item in payload.events if item.event_key not in received_keys]
    if not new_items:
        await session.commit()
        return SensorIngestResponse(
            accepted_events=0,
            duplicate_events=len(payload.events),
            stored_alerts=0,
        )

    sensor.last_event_at = max(item.event.timestamp for item in new_items)
    analysis = await run_analysis(
        AnalysisRunRequest(
            events=[item.event for item in new_items],
            as_of=datetime.now(timezone.utc),
            persist=True,
        ),
        session,
        sensor_actor,
        request,
    )
    for item, normalized_event_id in zip(new_items, analysis.stored_event_ids, strict=True):
        session.add(
            SensorEventReceipt(
                sensor_id=payload.sensor_id,
                event_key=item.event_key,
                normalized_event_id=normalized_event_id,
            )
        )
    await session.commit()
    return SensorIngestResponse(
        accepted_events=len(new_items),
        duplicate_events=len(payload.events) - len(new_items),
        stored_alerts=len(analysis.stored_alert_ids),
        workflow_id=analysis.workflow.workflow_id,
    )

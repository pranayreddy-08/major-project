from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password
from app.models import (
    Alert,
    AssetHost,
    AttackGraphEdge,
    AttackGraphNode,
    Explanation,
    Incident,
    NormalizedEvent,
    UserAccount,
    UserRole,
)
from app.models.entities import AlertStatus, IncidentStatus, Severity


def _id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"ecti-phase6-demo:{name}")


async def _seed_users(session: AsyncSession) -> None:
    settings = get_settings()
    existing = set((await session.scalars(select(UserAccount.username))).all())
    accounts = (
        (
            "analyst",
            "Demo Security Analyst",
            UserRole.analyst,
            settings.demo_analyst_password,
        ),
        (
            "admin",
            "Demo Platform Administrator",
            UserRole.administrator,
            settings.demo_admin_password,
        ),
    )
    for username, full_name, role, password in accounts:
        if username not in existing:
            session.add(
                UserAccount(
                    id=_id(f"user:{username}"),
                    username=username,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    role=role,
                    active=True,
                )
            )


async def _seed_dashboard_data(session: AsyncSession) -> None:
    if await session.get(NormalizedEvent, _id("event:auth-failure")) is not None:
        return

    incident = Incident(
        id=_id("incident:credential-compromise"),
        title="Credential attack progressing toward a critical asset",
        description=(
            "Repeated authentication failures and privileged access activity share a source, "
            "user, and host within the correlation window."
        ),
        status=IncidentStatus.investigating,
        severity=Severity.critical,
        risk_score=91.4,
    )
    session.add(incident)
    session.add(
        AssetHost(
            id=_id("asset:finance-api-01"),
            hostname="finance-api-01",
            ip_addresses=["198.51.100.20"],
            operating_system="Linux",
            owner="Finance Platform",
            criticality=0.95,
            attributes={"environment": "synthetic-demo"},
        )
    )

    event_specs = (
        (
            "auth-failure",
            datetime(2026, 8, 23, 8, 12, tzinfo=timezone.utc),
            "192.0.2.44",
            "198.51.100.20",
            "priya.analyst",
            "finance-api-01",
            "denied",
            Severity.high,
            "authentication_failure",
            {"anomaly_score": 0.86, "attempts": 18},
        ),
        (
            "credential-attack",
            datetime(2026, 8, 23, 8, 16, tzinfo=timezone.utc),
            "192.0.2.44",
            "198.51.100.20",
            "priya.analyst",
            "finance-api-01",
            "denied",
            Severity.critical,
            "credential_attack",
            {"anomaly_score": 0.96, "attempts": 31},
        ),
        (
            "privileged-login",
            datetime(2026, 8, 23, 8, 20, tzinfo=timezone.utc),
            "192.0.2.44",
            "198.51.100.20",
            "priya.analyst",
            "finance-api-01",
            "allowed",
            Severity.critical,
            "privileged_login",
            {"anomaly_score": 0.91, "new_device": True},
        ),
        (
            "endpoint-scan",
            datetime(2026, 8, 23, 8, 29, tzinfo=timezone.utc),
            "203.0.113.31",
            "198.51.100.35",
            None,
            "research-ws-04",
            "blocked",
            Severity.medium,
            "network_scan",
            {"anomaly_score": 0.61},
        ),
        (
            "heartbeat",
            datetime(2026, 8, 23, 8, 35, tzinfo=timezone.utc),
            "203.0.113.8",
            "198.51.100.30",
            "service-health",
            "monitor-01",
            "allowed",
            Severity.low,
            "heartbeat",
            {},
        ),
    )
    events: dict[str, NormalizedEvent] = {}
    for (
        key,
        timestamp,
        source_ip,
        destination_ip,
        user,
        host,
        action,
        severity,
        event_type,
        attributes,
    ) in event_specs:
        event = NormalizedEvent(
            id=_id(f"event:{key}"),
            timestamp=timestamp,
            source_ip=source_ip,
            destination_ip=destination_ip,
            user=user,
            host=host,
            protocol="tcp",
            action=action,
            severity=severity,
            log_source="phase6-synthetic-demo",
            event_type=event_type,
            attributes=attributes,
        )
        events[key] = event
        session.add(event)
    await session.flush()

    alert_specs = (
        (
            "auth-failure",
            "Repeated authentication failure",
            Severity.high,
            0.86,
            "Credential access",
        ),
        (
            "credential-attack",
            "Probable credential attack",
            Severity.critical,
            0.98,
            "Credential access",
        ),
        (
            "privileged-login",
            "Anomalous privileged login",
            Severity.critical,
            0.93,
            "Privilege escalation",
        ),
        (
            "endpoint-scan",
            "Blocked endpoint reconnaissance",
            Severity.medium,
            0.63,
            "Discovery",
        ),
    )
    alerts: dict[str, Alert] = {}
    for key, title, severity, confidence, alert_type in alert_specs:
        linked_incident = incident.id if key != "endpoint-scan" else None
        alert = Alert(
            id=_id(f"alert:{key}"),
            normalized_event_id=events[key].id,
            incident_id=linked_incident,
            alert_type=alert_type,
            title=title,
            description="Generated from deterministic synthetic Phase 6 demonstration data.",
            severity=severity,
            confidence=confidence,
            status=AlertStatus.open,
        )
        alerts[key] = alert
        session.add(alert)
    await session.flush()

    node_specs = (
        ("source", "ip", "192.0.2.44", 88.0),
        ("target", "ip", "198.51.100.20", 91.4),
        ("user", "user", "priya.analyst", 90.2),
        ("host", "host", "finance-api-01", 91.4),
    )
    nodes: dict[str, AttackGraphNode] = {}
    for key, entity_type, entity_key, risk_score in node_specs:
        node = AttackGraphNode(
            id=_id(f"node:{key}"),
            entity_type=entity_type,
            entity_key=entity_key,
            label=entity_key,
            risk_score=risk_score,
            attributes={"incident_id": str(incident.id)},
        )
        nodes[key] = node
        session.add(node)
    await session.flush()

    edge_specs = (
        ("source", "target", "network_connection", "auth-failure"),
        ("source", "host", "source_observed_on_host", "credential-attack"),
        ("user", "host", "user_activity", "credential-attack"),
        ("user", "target", "privileged_access", "privileged-login"),
    )
    for index, (source, target, relationship, event_key) in enumerate(edge_specs):
        session.add(
            AttackGraphEdge(
                id=_id(f"edge:{index}"),
                source_node_id=nodes[source].id,
                target_node_id=nodes[target].id,
                normalized_event_id=events[event_key].id,
                relationship_type=relationship,
                event_timestamp=events[event_key].timestamp,
                weight=1.0,
                attributes={"incident_id": str(incident.id)},
            )
        )

    for key in ("auth-failure", "credential-attack", "privileged-login"):
        alert = alerts[key]
        event = events[key]
        session.add(
            Explanation(
                id=_id(f"explanation:{key}"),
                alert_id=alert.id,
                method="phase5-v1-signals+graph-evidence",
                summary=(
                    f"{alert.title} was raised at {alert.confidence:.0%} confidence because "
                    f"severity={event.severity.value}, event_type={event.event_type}, and shared "
                    "entities form a time-ordered evidence path."
                ),
                evidence={
                    "important_features": [
                        {"name": "severity", "value": event.severity.value},
                        {"name": "event_type", "value": event.event_type},
                        {"name": "anomaly_score", "value": event.attributes["anomaly_score"]},
                    ],
                    "source_ip": event.source_ip,
                    "host": event.host,
                },
                limitations=(
                    "This explanation describes deterministic prototype evidence and does not "
                    "prove causality or malicious intent."
                ),
            )
        )


async def seed_development_data(session: AsyncSession) -> None:
    await _seed_users(session)
    await _seed_dashboard_data(session)
    await session.commit()

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents import WorkflowCoordinator
from app.core.audit import record_audit
from app.core.security import AuthenticatedUser, require_roles
from app.db.session import get_db_session
from app.intelligence.common import event_id
from app.intelligence.response import recommend_actions
from app.models import (
    Alert,
    AnalystFeedback,
    AttackGraphEdge,
    AttackGraphNode,
    AuditLog,
    Explanation,
    Incident,
    NormalizedEvent,
    UserRole,
)
from app.models.entities import AlertStatus, IncidentStatus, Severity
from app.schemas.intelligence import (
    AttackGraph,
    ResponseContext,
)
from app.schemas.intelligence import (
    AttackGraphEdge as GraphEdgeContract,
)
from app.schemas.intelligence import (
    AttackGraphNode as GraphNodeContract,
)
from app.schemas.platform import (
    AlertSummary,
    AnalysisRunRequest,
    AnalysisRunResult,
    AuditLogRead,
    DashboardOverview,
    EventIngestRequest,
    ExplanationRead,
    FeedbackCreate,
    FeedbackRead,
    IncidentDetail,
    IncidentSummary,
    RecommendationRead,
    SeverityCount,
    StoredEvent,
)
from app.schemas.workflow import WorkflowRequest

router = APIRouter(prefix="/platform", tags=["analyst platform"])
coordinator = WorkflowCoordinator()
analyst_or_admin = require_roles(UserRole.analyst, UserRole.administrator)
administrator_only = require_roles(UserRole.administrator)


def _severity_from_level(level: str) -> Severity:
    return Severity(level)


async def _incident_graph(session: AsyncSession, incident_id: UUID) -> AttackGraph:
    incident_key = str(incident_id)
    edges = list((await session.scalars(select(AttackGraphEdge))).all())
    selected_edges = [edge for edge in edges if edge.attributes.get("incident_id") == incident_key]
    node_ids = {
        node_id for edge in selected_edges for node_id in (edge.source_node_id, edge.target_node_id)
    }
    nodes = (
        list(
            (
                await session.scalars(
                    select(AttackGraphNode).where(AttackGraphNode.id.in_(node_ids))
                )
            ).all()
        )
        if node_ids
        else []
    )
    return AttackGraph(
        nodes=[
            GraphNodeContract(
                id=str(node.id),
                entity_type=node.entity_type,
                key=node.entity_key,
                label=node.label,
                risk_score=node.risk_score,
            )
            for node in sorted(nodes, key=lambda item: (item.entity_type, item.entity_key))
        ],
        edges=[
            GraphEdgeContract(
                id=str(edge.id),
                source=str(edge.source_node_id),
                target=str(edge.target_node_id),
                relationship=edge.relationship_type,
                event_id=str(edge.normalized_event_id or edge.id),
                timestamp=edge.event_timestamp,
            )
            for edge in sorted(selected_edges, key=lambda item: (item.event_timestamp, item.id))
        ],
    )


@router.get("/overview", response_model=DashboardOverview)
async def overview(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> DashboardOverview:
    open_alerts = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.status == AlertStatus.open)
    )
    active_incidents = await session.scalar(
        select(func.count()).select_from(Incident).where(Incident.status != IncidentStatus.closed)
    )
    critical_alerts = await session.scalar(
        select(func.count()).select_from(Alert).where(Alert.severity == Severity.critical)
    )
    monitored_events = await session.scalar(select(func.count()).select_from(NormalizedEvent))
    distribution_rows = (
        await session.execute(select(Alert.severity, func.count(Alert.id)).group_by(Alert.severity))
    ).all()
    distribution = {severity: count for severity, count in distribution_rows}
    recent = list(
        (await session.scalars(select(Alert).order_by(Alert.created_at.desc()).limit(5))).all()
    )
    return DashboardOverview(
        open_alerts=open_alerts or 0,
        active_incidents=active_incidents or 0,
        critical_alerts=critical_alerts or 0,
        monitored_events=monitored_events or 0,
        severity_distribution=[
            SeverityCount(severity=severity, count=distribution.get(severity, 0))
            for severity in Severity
        ],
        recent_alerts=[AlertSummary.model_validate(alert) for alert in recent],
        model_status="operational",
        model_name="severity-anomaly-baseline",
        model_version="1.0.0",
    )


@router.get("/events", response_model=list[StoredEvent])
async def list_events(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
) -> list[StoredEvent]:
    events = list(
        (
            await session.scalars(
                select(NormalizedEvent).order_by(NormalizedEvent.timestamp.desc()).limit(limit)
            )
        ).all()
    )
    return [StoredEvent.model_validate(event) for event in events]


@router.post("/events", response_model=StoredEvent, status_code=status.HTTP_201_CREATED)
async def ingest_event(
    payload: EventIngestRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
    request: Request,
) -> StoredEvent:
    values = payload.event.model_dump(exclude={"raw_event_id"})
    values["source_ip"] = str(payload.event.source_ip) if payload.event.source_ip else None
    values["destination_ip"] = (
        str(payload.event.destination_ip) if payload.event.destination_ip else None
    )
    values["severity"] = Severity(payload.event.severity.value)
    event = NormalizedEvent(**values)
    session.add(event)
    await session.flush()
    await record_audit(
        session,
        actor_username=user.username,
        action="event_ingested",
        resource_type="normalized_event",
        resource_id=str(event.id),
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(event)
    return StoredEvent.model_validate(event)


@router.get("/alerts", response_model=list[AlertSummary])
async def list_alerts(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
    severity: Severity | None = None,
    query: Annotated[str | None, Query(max_length=100)] = None,
) -> list[AlertSummary]:
    statement = select(Alert).order_by(Alert.created_at.desc())
    if severity:
        statement = statement.where(Alert.severity == severity)
    if query:
        statement = statement.where(Alert.title.ilike(f"%{query}%"))
    alerts = list((await session.scalars(statement.limit(250))).all())
    return [AlertSummary.model_validate(alert) for alert in alerts]


@router.get("/alerts/{alert_id}", response_model=AlertSummary)
async def get_alert(
    alert_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> AlertSummary:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertSummary.model_validate(alert)


@router.get("/alerts/{alert_id}/explanations", response_model=list[ExplanationRead])
async def alert_explanations(
    alert_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> list[ExplanationRead]:
    if await session.get(Alert, alert_id) is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    explanations = list(
        (
            await session.scalars(
                select(Explanation)
                .where(Explanation.alert_id == alert_id)
                .order_by(Explanation.created_at.desc())
            )
        ).all()
    )
    return [ExplanationRead.model_validate(item) for item in explanations]


@router.get("/alerts/{alert_id}/recommendations", response_model=RecommendationRead)
async def alert_recommendations(
    alert_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> RecommendationRead:
    alert = await session.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    event = (
        await session.get(NormalizedEvent, alert.normalized_event_id)
        if alert.normalized_event_id
        else None
    )
    incident = await session.get(Incident, alert.incident_id) if alert.incident_id else None
    recommendations = recommend_actions(
        ResponseContext(
            risk_score=incident.risk_score if incident else alert.confidence * 100,
            confidence=alert.confidence,
            event_type=event.event_type if event else alert.alert_type,
            host=event.host if event else None,
            user=event.user if event else None,
            source_ip=event.source_ip if event and event.source_ip else None,
            malicious_ip_confirmed=False,
        )
    )
    return RecommendationRead(alert_id=alert.id, recommendations=recommendations)


@router.get("/incidents", response_model=list[IncidentSummary])
async def list_incidents(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> list[IncidentSummary]:
    incidents = list(
        (
            await session.scalars(select(Incident).order_by(Incident.risk_score.desc()).limit(100))
        ).all()
    )
    return [IncidentSummary.model_validate(incident) for incident in incidents]


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
async def get_incident(
    incident_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> IncidentDetail:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    alerts = list(
        (
            await session.scalars(
                select(Alert).where(Alert.incident_id == incident_id).order_by(Alert.created_at)
            )
        ).all()
    )
    return IncidentDetail(
        incident=IncidentSummary.model_validate(incident),
        alerts=[AlertSummary.model_validate(alert) for alert in alerts],
        graph=await _incident_graph(session, incident_id),
    )


@router.get("/incidents/{incident_id}/graph", response_model=AttackGraph)
async def get_incident_graph(
    incident_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> AttackGraph:
    if await session.get(Incident, incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return await _incident_graph(session, incident_id)


@router.post("/analysis/run", response_model=AnalysisRunResult)
async def run_analysis(
    payload: AnalysisRunRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
    request: Request,
) -> AnalysisRunResult:
    workflow_request = WorkflowRequest.model_validate(payload.model_dump(exclude={"persist"}))
    workflow = coordinator.run(workflow_request)
    stored_events: dict[str, NormalizedEvent] = {}
    stored_alert_ids: list[UUID] = []
    if payload.persist:
        for incoming in workflow_request.events:
            values = incoming.model_dump(exclude={"raw_event_id"})
            values["source_ip"] = str(incoming.source_ip) if incoming.source_ip else None
            values["destination_ip"] = (
                str(incoming.destination_ip) if incoming.destination_ip else None
            )
            values["severity"] = Severity(incoming.severity.value)
            stored = NormalizedEvent(**values)
            session.add(stored)
            stored_events[event_id(incoming)] = stored
        await session.flush()

        incident_map: dict[str, Incident] = {}
        assessment_by_event = (
            {item.event_id: item for item in workflow.risk.assessments} if workflow.risk else {}
        )
        if workflow.correlation:
            for correlated in workflow.correlation.incidents:
                risk_scores = [
                    assessment_by_event[event_key].risk.score
                    for event_key in correlated.event_ids
                    if event_key in assessment_by_event
                ]
                risk_score = max(risk_scores, default=0.0)
                incident = Incident(
                    title=f"Correlated incident {correlated.id[-8:]}",
                    description=(
                        f"{len(correlated.event_ids)} events correlated by the phase5-v1 workflow."
                    ),
                    status=IncidentStatus.open,
                    severity=_severity_from_level(
                        max(
                            (
                                assessment_by_event[key].risk.level
                                for key in correlated.event_ids
                                if key in assessment_by_event
                            ),
                            key=lambda level: ["low", "medium", "high", "critical"].index(level),
                            default="low",
                        )
                    ),
                    risk_score=risk_score,
                )
                session.add(incident)
                incident_map[correlated.id] = incident
            await session.flush()

        alert_by_event: dict[str, Alert] = {}
        if workflow.detection:
            for finding in workflow.detection.findings:
                if finding.classification == "benign":
                    continue
                assessment = assessment_by_event.get(finding.event_id)
                incident_id = None
                if assessment and assessment.incident_ids:
                    incident_id = incident_map[assessment.incident_ids[0]].id
                alert = Alert(
                    normalized_event_id=stored_events[finding.event_id].id,
                    incident_id=incident_id,
                    alert_type=finding.classification,
                    title=f"{finding.classification.title()} activity detected",
                    description="Created by the authenticated Phase 6 analysis endpoint.",
                    severity=(
                        _severity_from_level(assessment.risk.level)
                        if assessment
                        else Severity.medium
                    ),
                    confidence=finding.confidence,
                    status=AlertStatus.open,
                )
                session.add(alert)
                alert_by_event[finding.event_id] = alert
            await session.flush()
            stored_alert_ids = [alert.id for alert in alert_by_event.values()]

        if workflow.explainability:
            for item in workflow.explainability.explanations:
                alert = alert_by_event.get(item.event_id)
                if alert:
                    session.add(
                        Explanation(
                            alert_id=alert.id,
                            method="phase5-v1-signals+graph-evidence",
                            summary=item.summary,
                            evidence={
                                "important_features": [
                                    feature.model_dump(mode="json")
                                    for feature in item.important_features
                                ],
                                "supporting_edge_ids": item.supporting_edge_ids,
                                "supporting_event_ids": item.supporting_event_ids,
                            },
                            limitations=item.limitations,
                        )
                    )

        if workflow.correlation and incident_map:
            node_map: dict[str, AttackGraphNode] = {}
            incident_id = next(iter(incident_map.values())).id
            for node in workflow.correlation.attack_graph.nodes:
                existing = await session.scalar(
                    select(AttackGraphNode).where(
                        AttackGraphNode.entity_type == node.entity_type,
                        AttackGraphNode.entity_key == node.key,
                    )
                )
                if existing is None:
                    existing = AttackGraphNode(
                        entity_type=node.entity_type,
                        entity_key=node.key,
                        label=node.label,
                        risk_score=node.risk_score,
                        attributes={"incident_id": str(incident_id)},
                    )
                    session.add(existing)
                    await session.flush()
                node_map[node.id] = existing
            for edge in workflow.correlation.attack_graph.edges:
                session.add(
                    AttackGraphEdge(
                        source_node_id=node_map[edge.source].id,
                        target_node_id=node_map[edge.target].id,
                        normalized_event_id=stored_events[edge.event_id].id,
                        relationship_type=edge.relationship,
                        event_timestamp=edge.timestamp,
                        attributes={"incident_id": str(incident_id)},
                    )
                )

    await record_audit(
        session,
        actor_username=user.username,
        action="analysis_run",
        resource_type="workflow",
        resource_id=workflow.workflow_id,
        detail={
            "status": workflow.status,
            "events": len(workflow_request.events),
            "alerts_persisted": len(stored_alert_ids),
            "persist": payload.persist,
        },
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    return AnalysisRunResult(
        workflow=workflow,
        stored_event_ids=[item.id for item in stored_events.values()],
        stored_alert_ids=stored_alert_ids,
    )


@router.post("/feedback", response_model=FeedbackRead, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    payload: FeedbackCreate,
    session: Annotated[AsyncSession, Depends(get_db_session)],
    user: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
    request: Request,
) -> FeedbackRead:
    if payload.alert_id is None and payload.incident_id is None:
        raise HTTPException(status_code=422, detail="alert_id or incident_id is required")
    if payload.alert_id and await session.get(Alert, payload.alert_id) is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    if payload.incident_id and await session.get(Incident, payload.incident_id) is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    feedback = AnalystFeedback(
        alert_id=payload.alert_id,
        incident_id=payload.incident_id,
        analyst=user.username,
        verdict=payload.verdict,
        comment=payload.comment,
    )
    session.add(feedback)
    await session.flush()
    await record_audit(
        session,
        actor_username=user.username,
        action="feedback_submitted",
        resource_type="analyst_feedback",
        resource_id=str(feedback.id),
        detail={"verdict": payload.verdict},
        ip_address=request.client.host if request.client else None,
    )
    await session.commit()
    await session.refresh(feedback)
    return FeedbackRead.model_validate(feedback)


@router.get("/feedback", response_model=list[FeedbackRead])
async def list_feedback(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(analyst_or_admin)],
) -> list[FeedbackRead]:
    items = list(
        (
            await session.scalars(
                select(AnalystFeedback).order_by(AnalystFeedback.created_at.desc()).limit(200)
            )
        ).all()
    )
    return [FeedbackRead.model_validate(item) for item in items]


@router.get("/audit-logs", response_model=list[AuditLogRead])
async def list_audit_logs(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    _: Annotated[AuthenticatedUser, Depends(administrator_only)],
) -> list[AuditLogRead]:
    logs = list(
        (
            await session.scalars(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(250))
        ).all()
    )
    return [AuditLogRead.model_validate(item) for item in logs]

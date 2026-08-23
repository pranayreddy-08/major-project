from datetime import timedelta

from fastapi import APIRouter

from app.intelligence.correlation import correlate_events
from app.intelligence.graph import build_attack_graph
from app.intelligence.response import recommend_actions
from app.intelligence.risk import calculate_risk
from app.schemas.intelligence import (
    AttackGraph,
    AttackGraphBuildRequest,
    CorrelatedIncident,
    CorrelationBuildRequest,
    ResponseContext,
    ResponseRecommendation,
    RiskInput,
    RiskResult,
)

router = APIRouter(prefix="/intelligence", tags=["intelligence"])


@router.post("/correlations/build", response_model=list[CorrelatedIncident])
async def build_correlations(request: CorrelationBuildRequest) -> list[CorrelatedIncident]:
    return correlate_events(
        request.events,
        window=timedelta(minutes=request.window_minutes),
    )


@router.post("/attack-graphs/build", response_model=AttackGraph)
async def create_attack_graph(request: AttackGraphBuildRequest) -> AttackGraph:
    return build_attack_graph(request.events)


@router.post("/risk/score", response_model=RiskResult)
async def score_risk(request: RiskInput) -> RiskResult:
    return calculate_risk(request)


@router.post("/recommendations", response_model=list[ResponseRecommendation])
async def create_recommendations(request: ResponseContext) -> list[ResponseRecommendation]:
    return recommend_actions(request)

from fastapi import APIRouter

from app.agents import (
    CorrelationAgent,
    DetectionAgent,
    ExplainabilityAgent,
    ResponseAgent,
    RiskAgent,
    WorkflowCoordinator,
)
from app.schemas.workflow import (
    CorrelationAgentRequest,
    CorrelationAgentResult,
    DetectionAgentRequest,
    DetectionAgentResult,
    ExplainabilityAgentRequest,
    ExplainabilityAgentResult,
    ResponseAgentRequest,
    ResponseAgentResult,
    RiskAgentRequest,
    RiskAgentResult,
    WorkflowRequest,
    WorkflowResult,
)

router = APIRouter(tags=["multi-agent workflow"])
detection_agent = DetectionAgent()
correlation_agent = CorrelationAgent()
risk_agent = RiskAgent()
explainability_agent = ExplainabilityAgent()
response_agent = ResponseAgent()
coordinator = WorkflowCoordinator(
    detection=detection_agent,
    correlation=correlation_agent,
    risk=risk_agent,
    explainability=explainability_agent,
    response=response_agent,
)


@router.post("/agents/detection/run", response_model=DetectionAgentResult)
async def run_detection(request: DetectionAgentRequest) -> DetectionAgentResult:
    return detection_agent.run(request)


@router.post("/agents/correlation/run", response_model=CorrelationAgentResult)
async def run_correlation(request: CorrelationAgentRequest) -> CorrelationAgentResult:
    return correlation_agent.run(request)


@router.post("/agents/risk/run", response_model=RiskAgentResult)
async def run_risk(request: RiskAgentRequest) -> RiskAgentResult:
    return risk_agent.run(request)


@router.post("/agents/explainability/run", response_model=ExplainabilityAgentResult)
async def run_explainability(
    request: ExplainabilityAgentRequest,
) -> ExplainabilityAgentResult:
    return explainability_agent.run(request)


@router.post("/agents/response/run", response_model=ResponseAgentResult)
async def run_response(request: ResponseAgentRequest) -> ResponseAgentResult:
    return response_agent.run(request)


@router.post("/workflows/analyze", response_model=WorkflowResult)
async def analyze_workflow(request: WorkflowRequest) -> WorkflowResult:
    return coordinator.run(request)

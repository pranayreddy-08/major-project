from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.workflows import router as workflow_router
from app.core.config import get_settings
from app.schemas.health import HealthResponse

settings = get_settings()

app = FastAPI(
    title="Explainable Cyber Threat Intelligence API",
    version="0.1.0",
    description="Decision-support API for explainable cyber threat intelligence.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(workflow_router, prefix="/api/v1")


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service="backend")

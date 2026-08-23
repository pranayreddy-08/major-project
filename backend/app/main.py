from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.auth import router as auth_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.platform import router as platform_router
from app.api.v1.workflows import router as workflow_router
from app.core.config import get_settings
from app.core.rate_limit import SlidingWindowRateLimiter
from app.core.security import get_current_user
from app.schemas.health import HealthResponse

settings = get_settings()
rate_limiter = SlidingWindowRateLimiter()

app = FastAPI(
    title="Explainable Cyber Threat Intelligence API",
    version="0.1.0",
    description="Decision-support API for explainable cyber threat intelligence.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def rate_limit_api(request: Request, call_next):
    if request.url.path.startswith("/api/v1/"):
        client = request.client.host if request.client else "unknown"
        is_login = request.url.path == "/api/v1/auth/token"
        limit = settings.login_rate_limit_per_minute if is_login else settings.rate_limit_per_minute
        key = f"{client}:{request.url.path if is_login else 'api'}"
        allowed, retry_after = rate_limiter.check(key, limit)
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
                headers={"Retry-After": str(retry_after)},
            )
    return await call_next(request)


app.include_router(auth_router, prefix="/api/v1")
app.include_router(platform_router, prefix="/api/v1")
app.include_router(
    intelligence_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)
app.include_router(
    workflow_router,
    prefix="/api/v1",
    dependencies=[Depends(get_current_user)],
)


@app.get("/health", response_model=HealthResponse, tags=["system"])
async def health_check() -> HealthResponse:
    return HealthResponse(status="healthy", service="backend")

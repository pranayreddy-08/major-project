from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_environment: str = Field(default="development", alias="APP_ENVIRONMENT")
    database_url: str = Field(
        default="postgresql+asyncpg://ecti:ecti@localhost:5432/ecti",
        alias="DATABASE_URL",
    )
    cors_origins: str = Field(default="http://localhost:5173", alias="CORS_ORIGINS")
    jwt_secret: str = Field(
        default="development-only-change-this-jwt-secret",
        min_length=32,
        alias="JWT_SECRET",
    )
    jwt_issuer: str = Field(default="ecti-platform", alias="JWT_ISSUER")
    jwt_audience: str = Field(default="ecti-dashboard", alias="JWT_AUDIENCE")
    access_token_expire_minutes: int = Field(
        default=30, ge=5, le=1440, alias="ACCESS_TOKEN_EXPIRE_MINUTES"
    )
    rate_limit_per_minute: int = Field(default=120, ge=10, alias="RATE_LIMIT_PER_MINUTE")
    login_rate_limit_per_minute: int = Field(default=10, ge=3, alias="LOGIN_RATE_LIMIT_PER_MINUTE")
    demo_analyst_password: str = Field(
        default="analyst-demo-only", min_length=12, alias="DEMO_ANALYST_PASSWORD"
    )
    demo_admin_password: str = Field(
        default="admin-demo-only", min_length=12, alias="DEMO_ADMIN_PASSWORD"
    )

    @property
    def cors_origin_list(self) -> list[str]:
        """Return configured comma-separated origins as individual URLs."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def production_must_override_demo_secrets(self) -> "Settings":
        if self.app_environment.lower() == "production":
            if self.jwt_secret == "development-only-change-this-jwt-secret":
                raise ValueError("JWT_SECRET must be changed in production")
            if self.demo_analyst_password == "analyst-demo-only":
                raise ValueError("DEMO_ANALYST_PASSWORD must be changed in production")
            if self.demo_admin_password == "admin-demo-only":
                raise ValueError("DEMO_ADMIN_PASSWORD must be changed in production")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()

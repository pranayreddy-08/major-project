from functools import lru_cache

from pydantic import Field
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


    @property
    def cors_origin_list(self) -> list[str]:
        '''Return configured comma-separated origins as individual URLs.'''
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()

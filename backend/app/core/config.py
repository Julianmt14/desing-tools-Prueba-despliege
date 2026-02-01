from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Design Tools API"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"

    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = "postgres"
    postgres_db: str = "design_tools"
    database_url: Optional[str] = None

    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_minutes: int = 60 * 24 * 7  # 7 días
    cors_origins: list[str] = ["http://localhost:3001"]
    allowed_origins: Optional[list[str]] = None

    DETALING_MAX_RECURSION_DEPTH: int = 10
    DETALING_COMPUTATION_TIMEOUT: int = 30  # segundos
    DETALING_OPTIMIZATION_ENABLED: bool = True
    DETALING_VALIDATION_STRICT: bool = True

    NSR10_DEFAULT_ENERGY_CLASS: str = "DES"
    NSR10_MIN_CONTINUOUS_BARS: int = 2
    NSR10_NO_SPLICE_ZONE_FACTOR: float = 2.0
    NSR10_MIN_POSITIVE_IN_SUPPORTS: float = 0.33

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors(cls, value):  # noqa: D401
        """Permite configurar orígenes como cadena separada por comas."""
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def split_allowed(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def sqlalchemy_database_uri(self) -> str:
        if self.database_url:
            return self.database_url
        return (
            f"postgresql+psycopg2://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

    @property
    def cors_origins_list(self) -> list[str]:
        return self.allowed_origins or self.cors_origins

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()

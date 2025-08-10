from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration with validation"""

    # GitHub API Configuration
    github_token: str = Field(..., description="GitHub API token")

    # CORS Configuration
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        description="Comma-separated list of allowed CORS origins",
    )

    # API Configuration
    api_timeout: float = Field(
        default=30.0,
        ge=1.0,
        le=120.0,
        description="API request timeout in seconds",
    )
    max_retries: int = Field(
        default=3, ge=0, le=10, description="Maximum number of API retries"
    )

    # Cache Configuration
    cache_ttl_repos: int = Field(
        default=300,
        ge=60,
        le=3600,
        description="Repository cache TTL in seconds",
    )
    cache_ttl_languages: int = Field(
        default=600,
        ge=60,
        le=3600,
        description="Languages cache TTL in seconds",
    )

    # Sentry Configuration
    sentry_dsn: Optional[str] = Field(
        default=None, description="Sentry DSN for error reporting"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")

    # Application Configuration
    app_name: str = Field(
        default="Weightless API", description="Application name"
    )
    app_version: str = Field(
        default="1.0.0", description="Application version"
    )
    debug: bool = Field(default=False, description="Debug mode")

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, v: str) -> List[str]:
        """Parse and validate CORS origins"""
        origins = [origin.strip() for origin in v.split(",")]
        return [
            origin for origin in origins if origin
        ]  # Filter out empty strings

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"Log level must be one of: {valid_levels}")
        return v_upper

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

        # Environment variable prefixes
        env_prefix = ""


# Global settings instance
settings = Settings()

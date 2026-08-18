from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Chronos"
    API_V1_STR: str = "/api/v1"
    ALLOWED_ORIGINS: List[str] = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://10.0.2.2:8000",
    ]

    # Database URL
    DATABASE_URL: str = "sqlite:///./chronos.db"

    # Supabase Configuration
    SUPABASE_URL: Optional[str] = None
    SUPABASE_ANON_KEY: Optional[str] = None
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None
    SUPABASE_JWT_SECRET: str = "test-jwt-secret-key-for-local-chronos-development-minimum-32-chars"

    # Configurable Chronos Transition Policies (Defaults)
    MINIMUM_SLEEP_OPPORTUNITY_HOURS: float = 6.0
    DEFAULT_TRANSITION_RATE_MINUTES_PER_DAY: float = 7.5
    MAX_FEASIBILITY_DURATION_DAYS: int = 180
    DEFAULT_STEP_SIZE_MINUTES: int = 15

    # Evaluation Tolerance Matrix in Minutes
    TOLERANCE_SUCCESS_MINUTES: int = 20
    TOLERANCE_ACCEPTABLE_MINUTES: int = 45
    TOLERANCE_MISSED_MINUTES: int = 90
    TOLERANCE_MISS_MINUTES: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()

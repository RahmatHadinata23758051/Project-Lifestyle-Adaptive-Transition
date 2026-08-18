from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Chronos Backend"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Configurable Chronos Policy Parameters (Not absolute medical claims)
    MINIMUM_SLEEP_OPPORTUNITY_HOURS: float = 6.0
    DEFAULT_TRANSITION_RATE_MINUTES_PER_DAY: float = 7.5  # 15 minutes per 2 days
    DEFAULT_STEP_SIZE_MINUTES: int = 15
    DEFAULT_STEP_INTERVAL_DAYS: int = 2
    
    # Evaluation tolerance thresholds (in minutes)
    TOLERANCE_SUCCESS_MINUTES: int = 20
    TOLERANCE_ACCEPTABLE_MINUTES: int = 45
    TOLERANCE_MISSED_MINUTES: int = 90

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


settings = Settings()

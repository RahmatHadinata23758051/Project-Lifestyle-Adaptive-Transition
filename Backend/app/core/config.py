from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Project Chronos Backend"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["*"]
    
    # Safe sleep and physiological constants
    MINIMUM_SAFE_SLEEP_HOURS: float = 6.0
    SAFE_DAILY_STEP_MINUTES: float = 7.5  # 15 minutes per 2 days
    
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

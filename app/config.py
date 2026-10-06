from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

BASE_DIR = Path(__file__).resolve().parent.parent

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # Core AI / VLM Settings
    GEMINI_API_KEY: str = Field(default="", description="Google Gemini API Key")
    GEMINI_MODEL: str = Field(default="gemini-3-flash-preview", description="Gemini model for video inspection")
    LOG_LEVEL: str = Field(default="INFO")

    # Storage Paths
    DATA_DIR: Path = Field(default=BASE_DIR / "data")
    UPLOADS_DIR: Path = Field(default=BASE_DIR / "data" / "uploads")
    EVIDENCE_DIR: Path = Field(default=BASE_DIR / "data" / "evidence")
    REPORTS_DIR: Path = Field(default=BASE_DIR / "data" / "reports")
    MAX_UPLOAD_SIZE_MB: int = Field(default=500)

    # Sewer Overflow Scoring Weights (Deterministic 0-100)
    WEIGHT_WATER: float = 0.35
    WEIGHT_TRASH_INSIDE: float = 0.25
    WEIGHT_TRASH_NEAR: float = 0.15
    WEIGHT_INLET_BLOCKED: float = 0.10
    WEIGHT_HAZARD: float = 0.10
    WEIGHT_WET_CONDITIONS: float = 0.05
    SEWER_OVERFLOW_FLOOR: float = 70.0

    # Notification & Alerting
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    ALERT_EMAIL_RECIPIENT: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    WEBHOOK_URL: str = ""

    def ensure_directories(self) -> None:
        """Ensure all runtime directories exist."""
        for path in [self.DATA_DIR, self.UPLOADS_DIR, self.EVIDENCE_DIR, self.REPORTS_DIR]:
            path.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()

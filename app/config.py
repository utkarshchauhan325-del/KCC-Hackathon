from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

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
    WEATHER_API_KEY: str = Field(default="", description="WeatherAPI Key for meteorological forecasting")
    TOMTOM_API_KEY: str = Field(default="", description="TomTom Traffic API Key for road congestion monitoring")
    LOG_LEVEL: str = Field(default="INFO")

    # Administrator Authentication
    ADMIN_EMAIL: str = Field(default="admin@pune.gov.in", description="Official administrator email")
    ADMIN_PASSWORD: str = Field(default="admin123", description="Administrator password")

    # Local per-frame segmentation + tracking (YOLOE open-vocabulary model, runs on CPU)
    DETECTOR_ENABLED: bool = True
    DETECTOR_MODEL: str = Field(default="yoloe-26s-seg.pt", description="Ultralytics YOLOE segmentation weights")
    DETECTOR_CONF: float = 0.25
    DETECTOR_VP_CONF: float = Field(default=0.1, description="Threshold for garbage classes learned from Gemini examples")
    DETECTOR_EXEMPLAR_FRAMES: int = Field(default=4, description="Frames Gemini marks garbage on to teach the detector")
    DETECTOR_IMGSZ: int = 640
    DETECTOR_FPS: float = Field(default=10.0, description="Frames per second of video to run the detector on")

    # Storage Paths
    DATA_DIR: Path = Field(default=BASE_DIR / "data")
    UPLOADS_DIR: Path = Field(default=BASE_DIR / "data" / "uploads")
    EVIDENCE_DIR: Path = Field(default=BASE_DIR / "data" / "evidence")
    REPORTS_DIR: Path = Field(default=BASE_DIR / "data" / "reports")
    MODELS_DIR: Path = Field(default=BASE_DIR / "data" / "models")
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
    ALERT_MIN_SEVERITY: int = 3  # hazards at or above this severity (1-5) alert the municipality
    ALERT_TIMEOUT_SECONDS: int = 20

    @field_validator("DATA_DIR", "UPLOADS_DIR", "EVIDENCE_DIR", "REPORTS_DIR", "MODELS_DIR")
    @classmethod
    def _resolve_against_project(cls, v: Path) -> Path:
        """Relative paths in .env (e.g. DATA_DIR=data) are relative to the project, not the CWD."""
        return v if v.is_absolute() else BASE_DIR / v

    def ensure_directories(self) -> None:
        """Ensure all runtime directories exist."""
        for path in [self.DATA_DIR, self.UPLOADS_DIR, self.EVIDENCE_DIR, self.REPORTS_DIR, self.MODELS_DIR]:
            path.mkdir(parents=True, exist_ok=True)

settings = Settings()
settings.ensure_directories()

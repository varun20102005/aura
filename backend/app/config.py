import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://aura:aurapass@localhost:5432/auradb")
    HYBRID_SEMANTIC_WEIGHT: float = float(os.getenv("HYBRID_SEMANTIC_WEIGHT", "0.5"))
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_dev_key")
    JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "1440"))
    
    # Optional Third-Party APIs
    GEMINI_API_KEY: str | None = os.getenv("GEMINI_API_KEY", None)

    # SMTP Configuration (Mailtrap)
    SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.mailtrap.io")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", "2525"))
    SMTP_USER: str | None = os.getenv("SMTP_USER", None)
    SMTP_PASS: str | None = os.getenv("SMTP_PASS", None)
    SMTP_FROM: str = os.getenv("SMTP_FROM", "aura@example.com")

    class Config:
        env_file = ".env"

settings = Settings()

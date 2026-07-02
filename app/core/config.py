from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    NOMBA_ENV: str = "sandbox"
    NOMBA_ACCOUNT_ID: str
    NOMBA_SUB_ACCOUNT_ID: str
    NOMBA_CLIENT_ID: str
    NOMBA_CLIENT_SECRET: str
    NOMBA_WEBHOOK_SECRET: str
    DATABASE_URL: str
    SECRET_KEY: str = "cadence-dev-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60
    PORT: int = 8000

    # Pydantic configuration to read from .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()

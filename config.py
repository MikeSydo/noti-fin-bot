import os
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine which .env file to use
# 'prod' is default, 'dev' loads .env.dev
ENV = os.getenv("ENV", "prod")
ENV_FILE = ".env.dev" if ENV == "dev" else ".env"

class Settings(BaseSettings):
    """App Settings."""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore"  # silently ignore unknown env vars
    )

    # App Info
    VERSION: str = "0.3.3"
    ENV_NAME: str = ENV
    CHANGELOG_URL: str = "https://github.com/MikeSydo/noti-fin-bot/blob/master/CHANGELOG.md"

    # Server Settings
    PORT: int = 8080
    DOMAIN_NAME: str = "localhost"

    # Webhook Settings
    WEBHOOK_URL: str | None = None
    WEBHOOK_PATH: str = "/webhook"

    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # Gemini
    GEMINI_API_KEY: str

    # Database
    DATABASE_URL: str

    # Security
    FERNET_KEY: str

    # Notion OAuth
    NOTION_CLIENT_ID: str
    NOTION_CLIENT_SECRET: str
    NOTION_REDIRECT_URI: str

    # AWS S3
    AWS_REGION: str
    AWS_S3_BUCKET_NAME: str
    AWS_ACCESS_KEY_ID: str
    AWS_SECRET_ACCESS_KEY: str

# Singleton instance
settings = Settings()
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """App Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore" # allow extra fields like the old ones if user hasn't removed them
    )

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
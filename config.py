from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """App Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    TELEGRAM_BOT_TOKEN: str

    # Gemini
    GEMINI_API_KEY: str

    # Notion
    NOTION_API_KEY: str | None = None
    NOTION_ACCOUNTS_DB_ID: str | None = None
    NOTION_EXPENSES_DB_ID: str | None = None
    NOTION_GROUP_EXPENSES_DB_ID: str | None = None
    NOTION_CATEGORIES_DB_ID: str | None = None

    # Database
    DATABASE_URL: str

    # Security
    FERNET_KEY: str

    # Notion OAuth (Future)
    NOTION_CLIENT_ID: str | None = None
    NOTION_CLIENT_SECRET: str | None = None
    NOTION_REDIRECT_URI: str | None = None

# Singleton instance
settings = Settings()
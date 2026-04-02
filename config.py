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
    NOTION_API_KEY: str
    NOTION_ACCOUNTS_DB_ID: str
    NOTION_EXPENSES_DB_ID: str
    NOTION_GROUP_EXPENSES_DB_ID: str
    NOTION_CATEGORIES_DB_ID: str

# Singleton instance
settings = Settings()
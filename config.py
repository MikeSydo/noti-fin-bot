from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """App Settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # Telegram
    TELEGRAM_BOT_TOKEN: str

# Singleton instance
settings = Settings()
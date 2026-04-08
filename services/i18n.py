import json
import os
import logging
from typing import Dict
from sqlalchemy.future import select
from database import AsyncSessionLocal
from models.user import User

logger = logging.getLogger(__name__)

# USER_LANGS_FILE = "user_langs.json"
LOCALES_DIR = "locales"

class I18n:
    def __init__(self):
        self.langs: Dict[str, Dict[str, str]] = {}
        self.user_langs: Dict[int, str] = {}
        self._load_locales()
        # Initial user langs are loaded asynchronously at bot startup

    def _load_locales(self):
        for lang_code in ["en", "uk"]:
            path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.langs[lang_code] = json.load(f)
            else:
                self.langs[lang_code] = {}

    async def load_user_langs_from_db(self):
        try:
            async with AsyncSessionLocal() as session:
                result = await session.execute(select(User.telegram_id, User.language))
                users = result.fetchall()
                for telegram_id, language in users:
                    if language:
                        self.user_langs[telegram_id] = language
        except Exception as e:
            logger.error(f"Failed to load user languages from DB: {e}")

    async def _save_user_lang_to_db(self, user_id: int, lang_code: str, username: str = None):
        try:
            from services.user_service import create_or_update_user
            await create_or_update_user(user_id, language=lang_code, username=username)
        except Exception as e:
            logger.error(f"Failed to save user {user_id} language/username to DB: {e}")

    async def set_user_lang(self, user_id: int, lang_code: str, username: str = None):
        """Async method to set language and save it to the DB."""
        logger.info(f"Setting language for user {user_id} to '{lang_code}' (username: {username})")
        self.user_langs[user_id] = lang_code
        await self._save_user_lang_to_db(user_id, lang_code, username=username)

    def get_user_lang(self, user_id: int) -> str | None:
        return self.user_langs.get(user_id)

    def get_text(self, key: str, user_id: int = None, lang_code: str = None, **kwargs) -> str:
        code = lang_code or (self.get_user_lang(user_id) if user_id else "uk")
        if code not in self.langs:
            logger.warning(f"Language code '{code}' not found. Defaulting to 'uk'.")
            code = "uk"

        text = self.langs.get(code, {}).get(key)
        if text is None:
            # Fallback
            text = self.langs.get("uk", {}).get(key, key)

        if isinstance(text, list):
            if kwargs:
                return [t.format(**kwargs) for t in text]
            return text

        try:
            return text.format(**kwargs)
        except Exception:
            return text

    def get_all_translations(self, key: str) -> list[str]:
        return [self.langs[lang].get(key, key) for lang in self.langs if key in self.langs[lang]]

i18n = I18n()

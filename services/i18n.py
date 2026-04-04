import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

USER_LANGS_FILE = "user_langs.json"
LOCALES_DIR = "locales"

class I18n:
    def __init__(self):
        self.langs: Dict[str, Dict[str, str]] = {}
        self.user_langs: Dict[int, str] = {}
        self._load_locales()
        self._load_user_langs()

    def _load_locales(self):
        for lang_code in ["en", "uk"]:
            path = os.path.join(LOCALES_DIR, f"{lang_code}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    self.langs[lang_code] = json.load(f)
            else:
                self.langs[lang_code] = {}

    def _load_user_langs(self):
        if os.path.exists(USER_LANGS_FILE):
            try:
                with open(USER_LANGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.user_langs = {int(k): v for k, v in data.items()}
            except Exception as e:
                logger.error(f"Failed to load user languages: {e}")

    def _save_user_langs(self):
        try:
            with open(USER_LANGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.user_langs, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Failed to save user languages: {e}")

    def set_user_lang(self, user_id: int, lang_code: str):
        self.user_langs[user_id] = lang_code
        self._save_user_langs()

    def get_user_lang(self, user_id: int) -> str | None:
        return self.user_langs.get(user_id)

    def get_text(self, key: str, user_id: int = None, lang_code: str = None, **kwargs) -> str:
        code = lang_code or (self.get_user_lang(user_id) if user_id else "uk")
        if code not in self.langs:
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

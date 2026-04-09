import pytest
import sys
import os
from unittest.mock import AsyncMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from services.i18n import I18n


@pytest.fixture
def i18n_instance():
    """Create a fresh I18n instance with mock locale data for testing."""
    instance = I18n.__new__(I18n)
    instance.user_langs = {}
    instance.langs = {
        "en": {
            "msg_main_menu": "🏠 Main menu",
            "grexp_saved": "Group expense saved!\n\n**{name}**",
            "graph_months": ["Jan", "Feb", "Mar"],
        },
        "uk": {
            "msg_main_menu": "🏠 Головне меню",
            "grexp_saved": "Спільну витрату збережено!\n\n**{name}**",
            "graph_months": ["Січ", "Лют", "Бер"],
        },
    }
    return instance


def test_get_text_existing_key_en(i18n_instance):
    """Test get_text returns English text for English user."""
    i18n_instance.user_langs[100] = "en"
    result = i18n_instance.get_text("msg_main_menu", user_id=100)
    assert result == "🏠 Main menu"


def test_get_text_existing_key_uk(i18n_instance):
    """Test get_text returns Ukrainian text for Ukrainian user."""
    i18n_instance.user_langs[200] = "uk"
    result = i18n_instance.get_text("msg_main_menu", user_id=200)
    assert result == "🏠 Головне меню"


def test_get_text_with_format_kwargs(i18n_instance):
    """Test get_text formats kwargs into the string template."""
    i18n_instance.user_langs[300] = "en"
    result = i18n_instance.get_text("grexp_saved", user_id=300, name="Party")
    assert result == "Group expense saved!\n\n**Party**"


def test_get_text_fallback_to_uk_when_lang_missing(i18n_instance):
    """Test get_text falls back to 'uk' when user's lang code is not loaded."""
    i18n_instance.user_langs[400] = "fr"  # Not loaded
    result = i18n_instance.get_text("msg_main_menu", user_id=400)
    assert result == "🏠 Головне меню"


def test_get_text_key_not_found_returns_key(i18n_instance):
    """Test get_text returns the key itself when key is missing from all langs."""
    i18n_instance.user_langs[500] = "en"
    result = i18n_instance.get_text("nonexistent_key", user_id=500)
    assert result == "nonexistent_key"


def test_get_text_list_value(i18n_instance):
    """Test get_text returns list correctly when value is a list."""
    i18n_instance.user_langs[600] = "en"
    result = i18n_instance.get_text("graph_months", user_id=600)
    assert isinstance(result, list)
    assert result[0] == "Jan"


def test_get_user_lang_returns_correct_lang(i18n_instance):
    """Test get_user_lang returns the stored language for a user."""
    i18n_instance.user_langs[700] = "uk"
    result = i18n_instance.get_user_lang(700)
    assert result == "uk"


def test_get_user_lang_returns_none_for_unknown(i18n_instance):
    """Test get_user_lang returns None for unknown user."""
    result = i18n_instance.get_user_lang(9999)
    assert result is None


def test_get_all_translations(i18n_instance):
    """Test get_all_translations returns values from all languages."""
    results = i18n_instance.get_all_translations("msg_main_menu")
    assert "🏠 Main menu" in results
    assert "🏠 Головне меню" in results


def test_get_all_translations_missing_key(i18n_instance):
    """Test get_all_translations returns empty list for missing key."""
    results = i18n_instance.get_all_translations("missing_key")
    assert results == []


@pytest.mark.asyncio
async def test_set_user_lang_updates_cache(i18n_instance):
    """Test set_user_lang updates in-memory cache."""
    with patch.object(i18n_instance, '_save_user_lang_to_db', new_callable=AsyncMock) as mock_save:
        await i18n_instance.set_user_lang(800, "en", username="user800")
        assert i18n_instance.user_langs[800] == "en"
        mock_save.assert_called_once_with(800, "en", username="user800")


@pytest.mark.asyncio
async def test_set_user_lang_calls_db_save(i18n_instance):
    """Test set_user_lang persists the language to the DB."""
    with patch.object(i18n_instance, '_save_user_lang_to_db', new_callable=AsyncMock) as mock_save:
        await i18n_instance.set_user_lang(900, "uk")
        mock_save.assert_called_once_with(900, "uk", username=None)

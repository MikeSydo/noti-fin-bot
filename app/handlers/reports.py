import logging
from aiogram import Router, F
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.fsm.context import FSMContext

from services.i18n import i18n
from models.user import User

router = Router()
logger = logging.getLogger(__name__)

@router.message(F.text.in_(i18n.get_all_translations('btn_analytics')))
async def start_analytics(message: Message, state: FSMContext, user: User):
    """
    Reworked Analytics: Instead of generating charts, 
    provide a direct link to the 'Stats' section in Notion.
    """
    user_id = message.from_user.id
    await state.clear()
    
    if not user.stats_page_id:
        await message.answer(i18n.get_text('msg_notion_connected_no_dbs', user_id))
        return

    # Notion URL format: https://www.notion.so/page_id_no_dashes
    stats_url = f"https://www.notion.so/{user.stats_page_id.replace('-', '')}"
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=i18n.get_text('btn_open_notion_stats', user_id),
                    url=stats_url
                )
            ]
        ]
    )
    
    await message.answer(
        i18n.get_text('msg_analytics_link', user_id),
        reply_markup=keyboard
    )

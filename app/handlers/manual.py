import logging

from aiogram import Router, F
from aiogram.filters import CommandStart, Command, StateFilter
from aiogram.fsm.state import any_state
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from app.keyboards.reply import get_main_menu, get_language_menu
from services.i18n import i18n
from services.user_service import get_user, clear_user_notion_data
from services.oauth_service import generate_oauth_url

logger = logging.getLogger(__name__)

router = Router()


@router.message(CommandStart(), StateFilter(any_state))
async def cmd_start(message: Message, state: FSMContext):
    """Answers for command /start and clears FSM."""
    await state.clear()
    user_id = message.from_user.id

    if i18n.get_user_lang(user_id) is None:
        await message.answer(
            i18n.get_text('msg_start_new_user', lang_code='uk'),
            reply_markup=await get_language_menu()
        )
    else:
        # Check if Notion is connected
        user = await get_user(user_id)
        if user and user.is_notion_connected and user.has_databases:
            workspace_name = user.notion_workspace_name or "Notion"
            await message.answer(
                i18n.get_text('msg_main_menu_connected', user_id, workspace=workspace_name),
                reply_markup=await get_main_menu(user_id)
            )
        else:
            # Show connect button
            oauth_url = await generate_oauth_url(user_id)
            keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(
                        text=i18n.get_text('btn_connect_notion', user_id),
                        url=oauth_url
                    )]
                ]
            )
            await message.answer(
                i18n.get_text('msg_notion_not_connected', user_id),
                reply_markup=keyboard,
                parse_mode="Markdown",
            )


@router.message(Command('connect'), StateFilter(any_state))
async def cmd_connect(message: Message, state: FSMContext):
    """Generate OAuth link for connecting Notion."""
    await state.clear()
    user_id = message.from_user.id

    user = await get_user(user_id)
    if user and user.is_notion_connected and user.has_databases:
        await message.answer(
            i18n.get_text('msg_already_connected', user_id, workspace=user.notion_workspace_name or "Notion"),
            reply_markup=await get_main_menu(user_id),
        )
        return

    oauth_url = await generate_oauth_url(user_id)
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=i18n.get_text('btn_connect_notion', user_id),
                url=oauth_url
            )]
        ]
    )
    await message.answer(
        i18n.get_text('msg_connect_notion', user_id),
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


@router.message(Command('disconnect'), StateFilter(any_state))
async def cmd_disconnect(message: Message, state: FSMContext):
    """Disconnect Notion integration."""
    await state.clear()
    user_id = message.from_user.id

    success = await clear_user_notion_data(user_id)
    if success:
        await message.answer(i18n.get_text('msg_disconnected', user_id))
    else:
        await message.answer(i18n.get_text('msg_disconnect_error', user_id))


@router.message(F.text.in_(i18n.get_all_translations('btn_change_language')), StateFilter(any_state))
async def cmd_change_language(message: Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    await message.answer(
        i18n.get_text('msg_choose_language', user_id),
        reply_markup=await get_language_menu()
    )


@router.message(F.text.in_(["🇺🇦 Українська", "🇬🇧 English"]), StateFilter(any_state))
async def process_language_selection(message: Message):
    user_id = message.from_user.id
    if message.text == "🇬🇧 English":
        lang = "en"
    else:
        lang = "uk"
    
    await i18n.set_user_lang(user_id, lang, username=message.from_user.username)

    # After language selection, check if Notion is connected
    user = await get_user(user_id)
    if user and user.is_notion_connected and user.has_databases:
        await message.answer(
            i18n.get_text('msg_main_menu', user_id, lang_code=lang),
            reply_markup=await get_main_menu(user_id)
        )
    else:
        oauth_url = await generate_oauth_url(user_id)
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(
                    text=i18n.get_text('btn_connect_notion', user_id, lang_code=lang),
                    url=oauth_url
                )]
            ]
        )
        await message.answer(
            i18n.get_text('msg_notion_not_connected', user_id, lang_code=lang),
            reply_markup=keyboard,
            parse_mode="Markdown",
        )


@router.message(Command('help'), StateFilter(any_state))
async def get_help(message: Message, state: FSMContext):
    """Answers for command /help."""
    user_id = message.from_user.id
    await message.answer(i18n.get_text('msg_help', user_id), parse_mode="Markdown")


@router.message(Command('cancel'), StateFilter(any_state))
@router.message(F.text.in_(i18n.get_all_translations('btn_cancel')), StateFilter(any_state))
async def cmd_cancel(message: Message, state: FSMContext):
    """Allows user to cancel any action."""
    user_id = message.from_user.id
    current_state = await state.get_state()

    logger.info("Cancelling state %r", current_state)
    await state.clear()
    await message.answer(
        i18n.get_text('msg_action_cancelled', user_id),
        reply_markup=await get_main_menu(user_id),
    )
@router.message(Command('version'), StateFilter(any_state))
async def cmd_version(message: Message):
    """Answers for command /version."""
    user_id = message.from_user.id
    from config import settings
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(
                text=i18n.get_text('btn_release_notes', user_id),
                url=settings.RELEASE_NOTES_URL
            )]
        ]
    )
    
    await message.answer(
        i18n.get_text(
            'msg_version', 
            user_id, 
            version=settings.VERSION, 
            env=settings.ENV_NAME.upper()
        ), 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

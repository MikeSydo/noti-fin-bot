import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from bot import bot
from decimal import Decimal

from services.i18n import i18n
from services.notion_writer import NotionWriter
from services.receipt_parser import parse_receipt
from models.group_expense import GroupExpense

router = Router()

logger = logging.getLogger(__name__)


@router.message(F.photo | F.document)
async def handle_receipt_image(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Handle image uploaded outside of any FSM state (meaning it's probably a receipt to parse)."""
    current_state = await state.get_state()
    if current_state is not None:
        return

    user_id = message.from_user.id
    # Using existing localization keys from uk.json/en.json
    processing_msg = await message.answer(i18n.get_text('rcp_analyzing', user_id))

    try:
        file_id = None
        if message.photo:
            file_id = message.photo[-1].file_id
        elif message.document:
            file_id = message.document.file_id

        if not file_id:
            await processing_msg.edit_text(i18n.get_text('rcp_invalid_file', user_id))
            return

        file = await bot.get_file(file_id)
        file_bytes = await bot.download_file(file.file_path)

        categories = await notion_writer.get_categories()
        category_names = [cat.name for cat in categories]

        # Use Gemini parser
        lang_code = i18n.get_user_lang(user_id) or "uk"
        parsed_data = await parse_receipt(file_bytes.read(), category_names, lang_code=lang_code)

        if not parsed_data or not parsed_data.is_receipt:
            await processing_msg.edit_text(i18n.get_text('rcp_not_receipt', user_id))
            return

        # Map ParsedReceipt to GroupExpense model
        try:
            # Parse date from DD-MM-YYYY
            expense_date = datetime.strptime(parsed_data.date, "%d-%m-%Y")
        except Exception:
            expense_date = datetime.now()

        # Find best category match from existing objects
        top_category = None
        if parsed_data.items and parsed_data.items[0].category_name:
            cat_name = parsed_data.items[0].category_name
            top_category = next((c for c in categories if c.name == cat_name), None)

        accounts = await notion_writer.get_accounts()
        default_account = accounts[0] if accounts else None

        group_expense = GroupExpense(
            name=parsed_data.group_expense_name,
            amount=Decimal(str(parsed_data.total_amount)),
            date=expense_date,
            account=default_account,
            category=top_category,
            receipt_url=f"https://api.telegram.org/file/bot{bot.token}/{file.file_path}"
        )

        success = await notion_writer.add_group_expense(group_expense)

        if success:
            await processing_msg.delete()
            skipped_text = i18n.get_text('txt_skipped', user_id)
            display_amount = f"{group_expense.amount:.2f}"
            account_name = group_expense.account.name if group_expense.account else skipped_text
            category_name = group_expense.category.name if group_expense.category else skipped_text
            
            await message.answer(
                i18n.get_text('rcp_saved', user_id, 
                              store_name=parsed_data.store_name, 
                              items_count=len(parsed_data.items)),
                parse_mode="Markdown"
            )
            # Show the saved data details using grexp_saved template
            await message.answer(
                i18n.get_text('grexp_saved', user_id, 
                              name=group_expense.name, 
                              amount=display_amount, 
                              date=group_expense.date.strftime("%d.%m.%Y"),
                              account=account_name, 
                              category=category_name),
                parse_mode="Markdown"
            )
        else:
            await processing_msg.edit_text(i18n.get_text('rcp_save_error', user_id))

    except Exception as e:
        logger.error(f"Failed to process receipt: {e}")
        await processing_msg.edit_text(i18n.get_text('rcp_save_error', user_id))
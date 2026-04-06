import logging
from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter
from bot import bot
from decimal import Decimal
from services.s3_service import upload_receipt_to_s3

from services.i18n import i18n
from services.notion_writer import NotionWriter
from services.receipt_parser import parse_receipt
from models.group_expense import GroupExpense
from models.expense import Expense
from app.keyboards.inline import get_accounts_keyboard
from app.keyboards.reply import get_main_menu

router = Router()

logger = logging.getLogger(__name__)

class ReceiptProcessingState(StatesGroup):
    waiting_for_account = State()

@router.message(StateFilter(None), F.photo | F.document)
async def handle_receipt_image(message: Message, state: FSMContext, notion_writer: NotionWriter):
    """Handle image uploaded outside of any FSM state (meaning it's probably a receipt to parse)."""
    user_id = message.from_user.id
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

        lang_code = i18n.get_user_lang(user_id) or "uk"
        bts = file_bytes.read()
        parsed_data = await parse_receipt(bts, category_names, lang_code=lang_code)

        if not parsed_data or not parsed_data.is_receipt:
            await processing_msg.edit_text(i18n.get_text('rcp_not_receipt', user_id))
            return

        # Fetch accounts to present to the user
        accounts = await notion_writer.get_accounts()
        if not accounts:
            await processing_msg.edit_text(i18n.get_text('rcp_no_accounts', user_id))
            return

        # Prepare state data for the next step
        # Upload image to S3 to get a permanent URL for Notion
        # Read the bytes into memory (they were consumed by parse_receipt, but wait, bts was read!)
        # We need to re-read or use the original bts
        file_url = await upload_receipt_to_s3(bts, file_extension="jpg")
        
        await state.update_data(
            parsed_data=parsed_data.model_dump(),
            file_url=file_url,
            processing_msg_id=processing_msg.message_id
        )

        await processing_msg.edit_text(
            i18n.get_text('rcp_identified', user_id, 
                          store_name=parsed_data.store_name, 
                          total_amount=parsed_data.total_amount,
                          items_count=len(parsed_data.items)),
            reply_markup=await get_accounts_keyboard(accounts, include_skip=True, user_id=user_id)
        )
        await state.set_state(ReceiptProcessingState.waiting_for_account)

    except Exception as e:
        logger.error(f"Failed to process receipt: {e}")
        await processing_msg.edit_text(i18n.get_text('rcp_save_error', user_id))


@router.callback_query((F.data.startswith('select_account_')) | (F.data == 'skip_account'), ReceiptProcessingState.waiting_for_account)
async def process_account_for_receipt(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    user_id = callback.from_user.id
    await callback.answer()
    
    if callback.data == 'skip_account':
        account = None
    else:
        account_id = callback.data.replace('select_account_', '')
        account = await notion_writer.get_account(account_id)
    
    data = await state.get_data()
    parsed_data_dict = data.get("parsed_data")
    file_url = data.get("file_url")
    processing_msg_id = data.get("processing_msg_id")

    await state.clear()
    
    saving_msg = await callback.message.edit_text(i18n.get_text('rcp_saving', user_id))

    try:
        from services.receipt_parser import ParsedReceipt
        parsed_data = ParsedReceipt(**parsed_data_dict)
        
        try:
            expense_date = datetime.strptime(parsed_data.date, "%d-%m-%Y")
        except Exception:
            expense_date = datetime.now()

        categories = await notion_writer.get_categories()
        
        # 1. Create individual expenses
        expense_ids = []
        for item in parsed_data.items:
            cat = next((c for c in categories if c.name == item.category_name), None)
            
            expense = Expense(
                name=item.name,
                amount=Decimal(str(item.amount)),
                date=expense_date,
                account=account,
                category=cat
            )
            # Save expense to Notion
            exp_id = await notion_writer.add_expense(expense)
            if exp_id:
                expense_ids.append(exp_id)

        # 2. Find overall category for the group expense (optional, taken from first item if exists)
        top_category = next((c for c in categories if parsed_data.items and c.name == parsed_data.items[0].category_name), None)

        # 3. Create Group Expense linking individual expenses
        group_expense = GroupExpense(
            name=parsed_data.group_expense_name,
            amount=Decimal(str(parsed_data.total_amount)),
            date=expense_date,
            account=account,
            category=top_category,
            receipt_url=file_url,
            expenses_relations=expense_ids
        )

        success = await notion_writer.add_group_expense(group_expense)

        if success:
            await saving_msg.delete()
            skipped_text = i18n.get_text('txt_skipped', user_id)
            display_amount = f"{group_expense.amount:.2f}"
            account_name = group_expense.account.name if group_expense.account else skipped_text
            category_name = group_expense.category.name if group_expense.category else skipped_text
            
            await bot.send_message(
                chat_id=user_id,
                text=i18n.get_text('rcp_saved', user_id, 
                                   store_name=parsed_data.store_name, 
                                   items_count=len(expense_ids)),
                parse_mode="Markdown"
            )
            await bot.send_message(
                chat_id=user_id,
                text=i18n.get_text('grexp_saved', user_id, 
                                   name=group_expense.name, 
                                   amount=display_amount, 
                                   date=group_expense.date.strftime("%d.%m.%Y"),
                                   account=account_name, 
                                   category=category_name),
                parse_mode="Markdown",
                reply_markup=await get_main_menu(user_id)
            )
        else:
            await saving_msg.edit_text(i18n.get_text('rcp_save_error', user_id))

    except Exception as e:
        logger.error(f"Failed to process receipt relations: {e}")
        await saving_msg.edit_text(i18n.get_text('rcp_save_error', user_id))
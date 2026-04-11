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
from services.image_service import compress_image

from services.i18n import i18n
from services.notion_writer import NotionWriter
from services.receipt_parser import parse_receipt
from models.group_expense import GroupExpense
from models.expense import Expense
from app.keyboards.inline import get_accounts_keyboard, get_receipt_confirm_keyboard
from app.keyboards.reply import get_main_menu

router = Router()

logger = logging.getLogger(__name__)

class ReceiptProcessingState(StatesGroup):
    waiting_for_confirmation = State()
    waiting_for_name = State()
    waiting_for_account = State()

async def format_receipt_report(user_id: int, parsed_data_dict: dict) -> str:
    """Formats a detailed receipt report with tables and alert emojis."""
    from services.receipt_parser import ParsedReceipt
    parsed_data = ParsedReceipt(**parsed_data_dict)
    
    # Check math consistency
    items_sum = sum(item.get("amount", 0) for item in parsed_data_dict.get("items", []))
    math_mismatch = abs(items_sum - parsed_data.total_amount) > 0.01
    
    uncertain_fields = parsed_data.uncertain_fields or []
    
    def get_alert(field_name: str) -> str:
        return " ⚠️" if field_name in uncertain_fields else ""

    total_alert = " ⚠️" if math_mismatch or "total_amount" in uncertain_fields else ""
    
    # 📂 Get first category as general one
    top_cat = parsed_data.items[0].category_name if parsed_data.items else "None"
    
    header = i18n.get_text('rcp_report_header', user_id)
    report = (
        f"{header}\n\n"
        f"{i18n.get_text('rcp_report_name', user_id, name=parsed_data.group_expense_name)}{get_alert('group_expense_name')}\n"
        f"{i18n.get_text('rcp_report_total', user_id, total=f'{parsed_data.total_amount:.2f}')}{total_alert}\n"
        f"{i18n.get_text('rcp_report_category', user_id, category=top_cat)}{get_alert('category')}\n"
        f"{i18n.get_text('rcp_report_date', user_id, date=parsed_data.date)}{get_alert('date')}\n"
    )
    
    if parsed_data.items:
        report += i18n.get_text('rcp_report_items_header', user_id) + "\n"
        # Monospace table
        report += "```\n"
        # Widths
        NW = 25  # Name Width
        CW = 22  # Category Width
        SW = 15   # Sum Width
        
        # Header and Separator
        h_n = i18n.get_text('rcp_table_n', user_id)
        h_nm = i18n.get_text('rcp_table_name', user_id)
        h_sm = i18n.get_text('rcp_table_sum', user_id)
        h_ct = i18n.get_text('rcp_table_category', user_id)
        
        # Center the labels within their fixed widths
        header_line = f"{h_n:<2}| {h_nm:^{NW}} | {h_sm:^{SW}} | {h_ct:^{CW}}"
        sep_line = "-" * len(header_line)
        
        report += f"{header_line}\n{sep_line}\n"
        
        for i, item in enumerate(parsed_data.items, 1):
            alert = " ⚠️" if item.is_uncertain else ""
            
            # Truncation logic with dots
            nm = item.name.strip()
            if len(nm) > NW:
                nm = nm[:NW-2] + ".."
            
            ct = item.category_name.strip() if item.category_name else "-"
            if len(ct) > CW:
                ct = ct[:CW-2] + ".."
            
            # Formatting
            report += f"{i:<2}| {nm:^{NW}} | {item.amount:>{SW}.2f} | {ct:<{CW}}{alert}\n"
        
        # Add Total row
        report += f"{sep_line}\n"
        total_label = i18n.get_text('rcp_table_total', user_id)
        
        # Calculate total table width from header (excluding potential trailing spaces)
        total_width = len(sep_line)
        amount_str = f"{parsed_data.total_amount:.2f}"
        
        # Align: Total label (left) ... Amount (right) |
        # Using total_width - 2 to account for the trailing " |" padding in rows
        report += f"{total_label:<{total_width - len(amount_str) - 2}} {amount_str} |\n"
        report += "```"
        
        if math_mismatch:
            report += f"\n\n{i18n.get_text('rcp_math_mismatch', user_id, items_sum=items_sum, total_amount=parsed_data.total_amount)}"

    return report


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
        
        # Determine extension and mime-type
        extension = file.file_path.split('.')[-1].lower() if '.' in file.file_path else "jpg"
        
        # Compress image before parsing and uploading
        if extension != "pdf":
            bts = compress_image(bts)
        
        mime_type = "application/pdf" if extension == "pdf" else f"image/{extension}"
        if extension in ["jpg", "jpeg"]:
            mime_type = "image/jpeg"

        parsed_data = await parse_receipt(bts, category_names, lang_code=lang_code, mime_type=mime_type)

        if not parsed_data or not parsed_data.is_receipt:
            await processing_msg.edit_text(i18n.get_text('rcp_not_receipt', user_id))
            return

        # New Unified Workflow
        score = parsed_data.confidence_score
        
        # Red Zone (< 50%) - Still reject if very low
        if score < 50:
            await processing_msg.edit_text(i18n.get_text('rcp_confidence_low', user_id, confidence=score))
            return

        # Prepare state data for confirmation
        extension = file.file_path.split('.')[-1] if '.' in file.file_path else "jpg"
        file_url = await upload_receipt_to_s3(bts, file_extension=extension)
        
        await state.update_data(
            parsed_data=parsed_data.model_dump(),
            file_url=file_url,
            processing_msg_id=processing_msg.message_id
        )

        report_text = await format_receipt_report(user_id, parsed_data.model_dump())
        
        if score < 100:
            report_text = i18n.get_text('rcp_confidence_medium', user_id, confidence=score) + "\n\n" + report_text

        await processing_msg.edit_text(
            report_text,
            reply_markup=await get_receipt_confirm_keyboard(user_id),
            parse_mode="Markdown"
        )
        await state.set_state(ReceiptProcessingState.waiting_for_confirmation)

    except Exception as e:
        logger.error(f"Failed to process receipt: {e}")
        error_str = str(e).upper()
        if "503" in error_str or "UNAVAILABLE" in error_str or "BUSY" in error_str or "EXHAUSTED" in error_str:
            await processing_msg.edit_text(i18n.get_text('rcp_gemini_busy', user_id))
        else:
            await processing_msg.edit_text(i18n.get_text('rcp_analysis_error', user_id))


@router.callback_query(F.data == 'confirm_receipt', ReceiptProcessingState.waiting_for_confirmation)
async def confirm_receipt_callback(callback: CallbackQuery, state: FSMContext, notion_writer: NotionWriter):
    user_id = callback.from_user.id
    await callback.answer()
    
    accounts = await notion_writer.get_accounts()
    if not accounts:
        await callback.message.edit_text(i18n.get_text('rcp_no_accounts', user_id))
        return

    data = await state.get_data()
    parsed_data_dict = data.get("parsed_data")
    from services.receipt_parser import ParsedReceipt
    parsed_data = ParsedReceipt(**parsed_data_dict)

    # Ask for account
    await callback.message.edit_text(
        i18n.get_text('rcp_identified', user_id, 
                      store_name=parsed_data.store_name, 
                      total_amount=parsed_data.total_amount,
                      items_count=len(parsed_data.items)),
        reply_markup=await get_accounts_keyboard(accounts, include_skip=True, user_id=user_id)
    )
    await state.set_state(ReceiptProcessingState.waiting_for_account)


@router.callback_query(F.data == 'edit_receipt_name', ReceiptProcessingState.waiting_for_confirmation)
async def edit_receipt_name_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.answer()
    await callback.message.answer(i18n.get_text('rcp_enter_new_name', user_id))
    await state.set_state(ReceiptProcessingState.waiting_for_name)


@router.message(ReceiptProcessingState.waiting_for_name)
async def process_new_receipt_name(message: Message, state: FSMContext):
    user_id = message.from_user.id
    new_name = message.text.strip()
    
    if not new_name:
        return

    data = await state.get_data()
    parsed_dict = data.get("parsed_data")
    parsed_dict["group_expense_name"] = new_name
    
    await state.update_data(parsed_data=parsed_dict)
    await message.answer(i18n.get_text('rcp_name_updated', user_id, name=new_name))
    
    # Re-display report
    report_text = await format_receipt_report(user_id, parsed_dict)
    await message.answer(
        report_text,
        reply_markup=await get_receipt_confirm_keyboard(user_id),
        parse_mode="Markdown"
    )
    await state.set_state(ReceiptProcessingState.waiting_for_confirmation)


@router.callback_query(F.data == 'cancel_receipt', ReceiptProcessingState.waiting_for_confirmation)
async def cancel_receipt_callback(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    await callback.answer(i18n.get_text('msg_action_cancelled', user_id))
    await callback.message.delete()
    await state.clear()


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
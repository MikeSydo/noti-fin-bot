from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup, default_state
from aiogram.fsm.context import FSMContext
from datetime import datetime
from services.receipt_parser import parse_receipt
from services.notion_writer import notion_writer
from app.keyboards.inline import get_accounts_keyboard
from models.expense import Expense
from models.group_expense import GroupExpense
import filetype

router = Router()

class ScanReceiptState(StatesGroup):
    waiting_for_account = State()

@router.message(F.photo, default_state)
async def get_receipt(message: Message, state: FSMContext, bot: Bot):
    wait_msg = await message.answer("Аналізую зображення чеку... Це може зайняти до хвилини часу.")
    photo = message.photo[-1]
    
    # Download photo
    file_info = await bot.get_file(photo.file_id)
    downloaded_file = await bot.download_file(file_info.file_path)
    image_bytes = downloaded_file.read()
    
    # Verify it is an image
    kind = filetype.guess(image_bytes)
    if not kind or not kind.mime.startswith('image/'):
        await wait_msg.delete()
        await message.answer("Завантажений файл не схожий на дійсне зображення.")
        return
        
    categories = await notion_writer.get_categories()
    category_names = [cat.name for cat in categories]
    
    parsed_receipt = await parse_receipt(image_bytes, category_names)
    await wait_msg.delete()
    if not parsed_receipt:
        await message.answer("Не вдалося розпізнати чек. Переконайтеся, що фотографія чітка і містить чек.")
        return
        
    if not parsed_receipt.is_receipt:
        await message.answer("Це зображення не схоже на чек. Будь ласка, надішліть фотографію чеку.")
        return

    # Ask for account
    accounts = await notion_writer.get_accounts()
    if not accounts:
        await message.answer("Акаунти не знайдено. Будь ласка, спочатку додайте акаунт.")
        return
        
    await state.update_data(
        parsed_receipt=parsed_receipt.model_dump(),
        # TODO: Upload receipt image to AWS S3 before deployment.
        # Notion API requires a persistent external URL for attachments.
        # Since Telegram file URLs expire, we need to upload `image_bytes` to an S3 bucket
        # using 'boto3', get the public URL (or pre-signed URL), and pass it to GroupExpense.
    )
    await state.set_state(ScanReceiptState.waiting_for_account)
    await message.answer(
        f"Чек ідентифіковано: {parsed_receipt.store_name} ({parsed_receipt.total_amount})\n"
        f"Знайдено {len(parsed_receipt.items)} товарів.\n"
        f"З якого акаунта була здійснена ця витрата?",
        reply_markup=await get_accounts_keyboard(accounts, include_skip=True)
    )

@router.callback_query(F.data.startswith('select_account_'), ScanReceiptState.waiting_for_account)
async def process_receipt_account_selection(callback: CallbackQuery, state: FSMContext):
    account_id = callback.data.split('_')[2]
    await handle_save_receipt(callback.message, state, account_id)
    await callback.answer()

@router.callback_query(F.data == 'skip_account', ScanReceiptState.waiting_for_account)
async def process_receipt_account_skip(callback: CallbackQuery, state: FSMContext):
    await handle_save_receipt(callback.message, state, None)
    await callback.answer()

async def handle_save_receipt(message: Message, state: FSMContext, account_id: str | None):
    data = await state.get_data()
    parsed_dict = data.get("parsed_receipt")
    
    if not parsed_dict:
        await message.answer("Сесія закінчилась або дані недійсні.")
        await state.clear()
        return
        
    saving_msg = await message.answer("Зберігаю витрати в Notion...")

    account = None
    if account_id:
        account = await notion_writer.get_account(account_id)
        
    categories = await notion_writer.get_categories()
    cat_map = {c.name.lower(): c for c in categories}
    
    expense_ids = []
    
    # Save expenses
    for item in parsed_dict["items"]:
        cat_obj = None
        if item.get("category_name"):
            cat_obj = cat_map.get(item["category_name"].lower())
            
        try:
            item_date = datetime.strptime(parsed_dict["date"], "%d-%m-%Y")
        except:
            item_date = datetime.now()
            
        exp = Expense(
            name=f"{item['name']} ({parsed_dict['store_name']})",
            amount=item["amount"],
            date=item_date,
            account=account,
            category=cat_obj
        )
        exp_id = await notion_writer.add_expense(exp)
        if exp_id:
            expense_ids.append(exp_id)
            
    # Save group expense
    try:
        group_date = datetime.strptime(parsed_dict["date"], "%d-%m-%Y")
    except:
        group_date = datetime.now()
        
    group_name = parsed_dict.get("group_expense_name", f"Receipt from {parsed_dict['store_name']}")
        
    group_exp = GroupExpense(
        name=group_name,
        amount=parsed_dict["total_amount"],
        date=group_date,
        account=account,
        expenses_relations=expense_ids
    )
    
    success = await notion_writer.add_group_expense(group_exp)
    await saving_msg.delete()
    if success:
        await message.answer(f"Успішно збережено чек з {parsed_dict['store_name']} ({len(expense_ids)} товарів).")
    else:
        await message.answer("Виникла помилка під час збереження чека в Notion.")

    await state.clear()
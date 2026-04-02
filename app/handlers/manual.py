from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from app.keyboards.reply import get_main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Головне меню!', reply_markup=await get_main_menu())

@router.message(Command('help'))
async def get_help(message: Message):
    help_text = (
        "🤖 *Бот для обліку фінансів у Notion*\n\n"
        "Я допоможу швидко додавати ваші витрати до бази даних.\n\n"
        "📌 *Основні команди:*\n"
        "/start - Відкрити головне меню\n"
        "/help - Показати цю довідку\n"
        "/cancel - Скасувати поточну дію (якщо ви, наприклад, передумали вводити витрату)\n\n"
        "📸 *Сканування чеків:*\n"
        "Просто надішліть мені чітке фото фіскального чека, і я автоматично розпізнаю товари та додам їх до вашого Notion."
    )
    await message.answer(help_text, parse_mode="Markdown")

@router.message(Command('cancel'))
async def cmd_cancel(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Немає активних дій для скасування.", reply_markup=await get_main_menu())
        return

    await state.clear()
    await message.answer(
        "Дію успішно скасовано.",
        reply_markup=await get_main_menu()
    )

from aiogram import Router
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from app.keyboards.start_menu import get_main_menu

router = Router()

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer('Головне меню!', reply_markup=await get_main_menu())

@router.message(Command('help'))
async def get_help(message: Message):
    await message.answer('Help!')

@router.message(Command('cancel'))
async def get_help(message: Message):
    await message.answer('Cancel!')

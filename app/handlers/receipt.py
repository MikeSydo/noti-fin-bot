from aiogram import Router, F
from aiogram.types import Message

router = Router()

@router.message(F.photo)
async def get_receipt(message: Message):
    pass
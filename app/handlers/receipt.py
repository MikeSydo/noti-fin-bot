from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.state import default_state

router = Router()

@router.message(F.photo, default_state)
async def get_receipt(message: Message):
    pass
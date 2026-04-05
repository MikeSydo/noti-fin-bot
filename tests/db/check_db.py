import asyncio
from database import AsyncSessionLocal
from models.user import User
from sqlalchemy import select

async def run():
    async with AsyncSessionLocal() as s:
        res = await s.execute(select(User))
        users = res.scalars().all()
        with open('output_db.txt', 'w', encoding='utf-8') as f:
            f.write(str([{
                'id': u.telegram_id, 
                'acc': u.accounts_db_id, 
                'exp': u.expenses_db_id, 
                'cat': u.categories_db_id, 
                'grp': u.group_expenses_db_id
            } for u in users]))


if __name__ == '__main__':
    asyncio.run(run())

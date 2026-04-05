import asyncio
import json
from database import AsyncSessionLocal
from models.user import User
from sqlalchemy import select
from services.security import decrypt_token
from notion_client import AsyncClient

async def get_schema():
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).limit(1))
        user = result.scalars().first()
        if not user:
            return
        token = decrypt_token(user.notion_access_token_encrypted)
        client = AsyncClient(auth=token, notion_version="2022-06-28")
        db = await client.databases.retrieve(user.group_expenses_db_id)
        
        props = {}
        for k, v in db["properties"].items():
            props[k] = v['type']
            
        with open('schema.txt', 'w', encoding='utf-8') as f:
            f.write(json.dumps(props, indent=2))

asyncio.run(get_schema())

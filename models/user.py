from sqlalchemy import Column, String, BigInteger, LargeBinary
from database import Base

class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(BigInteger, primary_key=True)
    language = Column(String(5), default="uk")
    username = Column(String(255), nullable=True)

    # Notion credentials
    notion_access_token_encrypted = Column(LargeBinary, nullable=True)

    # IDs of the user's personal databases
    accounts_db_id = Column(String(100), nullable=True)
    expenses_db_id = Column(String(100), nullable=True)
    group_expenses_db_id = Column(String(100), nullable=True)
    categories_db_id = Column(String(100), nullable=True)


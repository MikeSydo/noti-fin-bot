from sqlalchemy import Column, String, BigInteger, LargeBinary, DateTime, func
from db import Base


class User(Base):
    __tablename__ = 'users'

    telegram_id = Column(BigInteger, primary_key=True)
    username = Column(String(255), nullable=True)
    language = Column(String(5), default="en", nullable=False)

    # Notion OAuth tokens (encrypted with Fernet)
    notion_access_token_encrypted = Column(LargeBinary, nullable=True)
    notion_refresh_token_encrypted = Column(LargeBinary, nullable=True)

    # Notion workspace metadata
    notion_bot_id = Column(String(100), nullable=True)
    notion_workspace_id = Column(String(100), nullable=True)
    notion_workspace_name = Column(String(255), nullable=True)
    notion_template_name = Column(String(255), nullable=True)

    # User's personal Notion database IDs (discovered from duplicated template)
    accounts_db_id = Column(String(100), nullable=True)
    expenses_db_id = Column(String(100), nullable=True)
    group_expenses_db_id = Column(String(100), nullable=True)
    categories_db_id = Column(String(100), nullable=True)
    stats_page_id = Column(String(100), nullable=True)

    # OAuth CSRF protection
    oauth_state = Column(String(255), nullable=True, index=True)
    oauth_state_expires = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    @property
    def is_notion_connected(self) -> bool:
        """Check if user has a valid Notion connection."""
        return self.notion_access_token_encrypted is not None

    @property
    def has_databases(self) -> bool:
        """Check if user has all required database IDs configured."""
        return all([
            self.accounts_db_id,
            self.expenses_db_id,
            self.group_expenses_db_id,
            self.categories_db_id,
        ])

from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional
from datetime import datetime
from .category import Category
from .account import Account

class Expense(BaseModel):
    id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
    #decription names should be like attributes names in notion db
    name: str = Field(..., description='Expense')
    amount: Decimal = Field(gte=0, description="Amount")
    date: datetime = Field(..., description="Date")
    account: Account | None = Field(...)
    category_id: str = Field(...)

    def to_notion_properties(self) -> dict:
        return {
            "Expense": {"title": [{"text": {"content": self.name}}]},
            "Amount": {"number": float(self.amount)},
            "Date": {"date": {"start": self.date.isoformat()}},
            "Account": {"relation": [{"id": self.account.id}]},
            "Category": {"relation": [{"id": self.category_id}]},
        }
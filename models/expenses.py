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
    amount: Decimal = Field(ge=0, description="Amount")
    date: datetime = Field(..., description="Date")
    account: Optional[Account] | None = Field(default=None)
    category: Optional[Category] | None = Field(default=None)

    def to_notion_properties(self) -> dict:
        properties = {
            "Expense": {"title": [{"text": {"content": self.name}}]},
            "Amount": {"number": float(self.amount)},
            "Date": {"date": {"start": self.date.isoformat()}},
        }
        if self.account and self.account.id:
            properties["Account"] = {"relation": [{"id": self.account.id}]}
        
        if self.category and self.category.id:
            properties["Category"] = {"relation": [{"id": self.category.id}]}
            
        return properties
from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional
from datetime import datetime
from .category import Category
from .account import Account

class GroupExpense(BaseModel):
    id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
    #decription names should be like attributes names in notion db
    name: str = Field(..., description='Group Expense')
    amount: Decimal = Field(ge=0, description="Amount")
    date: datetime = Field(..., description="Date")
    account: Optional[Account] = Field(default=None)
    category: Optional[Category] = Field(default=None)
    receipt_url: Optional[str] = Field(default=None, description="Receipt URL")

    def to_notion_properties(self) -> dict:
        properties = {
            "Group Expense": {"title": [{"text": {"content": self.name}}]},
            "Amount": {"number": float(self.amount)},
            "Date": {"date": {"start": self.date.isoformat()}},
        }
        if self.account and self.account.id:
            properties["Account"] = {"relation": [{"id": self.account.id}]}

        if self.category and self.category.id:
            properties["Category"] = {"relation": [{"id": self.category.id}]}

        if self.receipt_url:
            properties["Receipt"] = {
                "files": [
                    {
                        "type": "external",
                        "name": "receipt",
                        "external": {"url": self.receipt_url}
                    }
                ]
            }

        return properties


from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional

class Account(BaseModel):
    id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(..., description='Account')
    initial_amount: Optional[Decimal] | None = Field(default=None, ge=0, description="Initial Amount")
    monthly_budget: Optional[Decimal] | None = Field(default=None, ge=0, description="Monthly Budget")

    def to_notion_properties(self) -> dict:
        properties = {
            "Account": {"title": [{"text": {"content": self.name}}]},
        }
        if self.initial_amount is not None:
            properties["Initial Amount"] = {"number": float(self.initial_amount)}
        if self.monthly_budget is not None:
            properties["Monthly Budget"] = {"number": float(self.monthly_budget)}
        return properties

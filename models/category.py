from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional


class Category(BaseModel):
    id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
    # decription names should be like attributes names in notion db
    name: str = Field(..., description='Category')
    monthly_budget: Optional[Decimal] | None = Field(default=None, ge=0, description="Monthly Budget")

    def to_notion_properties(self) -> dict:
        return {
            "Category": {"title": [{"text": {"content": self.name}}]},
            "Monthly Budget": {"number": float(self.monthly_budget) if self.monthly_budget else None},
        }

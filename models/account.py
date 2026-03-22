from pydantic import BaseModel, Field, ConfigDict
from decimal import Decimal
from typing import Optional

class Account(BaseModel):
    id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
    #decription names should be like attributes names in notion db
    name: str = Field(..., description='Account')
    initial_amount: Optional[Decimal] = Field(default=None, gte=0, description="Initial Amount")

    def to_notion_properties(self) -> dict:
        return {
            "Account": {"title": [{"text": {"content": self.name}}]},
            "Initial Amount": {"number": float(self.initial_amount) if self.initial_amount else None},
        }
    
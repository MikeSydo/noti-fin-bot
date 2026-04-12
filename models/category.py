from pydantic import BaseModel, Field, ConfigDict
from typing import Optional


class Category(BaseModel):
    id: Optional[str] = None
    model_config = ConfigDict(populate_by_name=True)
    name: str = Field(..., description='Category')

    def to_notion_properties(self) -> dict:
        properties = {
            "Category": {"title": [{"text": {"content": self.name}}]},
        }
        return properties

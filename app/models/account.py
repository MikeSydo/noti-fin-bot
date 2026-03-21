from pydantic import BaseModel, Field
from decimal import Decimal

class Account(BaseModel):
    #decription names should be like attributes names in notion db
    name: str = Field(..., description='Account')
    initial_amount: Decimal = Field(..., gt=0, description="Initial Amount")
    
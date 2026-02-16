from datetime import datetime

from pydantic import BaseModel, computed_field

from app.custom_enums import PlanType


class PlanModel(BaseModel):
    """Pydantic model for Plan database entity."""

    id: int
    name: PlanType
    price: int  # Price in cents
    monthly_analyses: int | None  # None = Unlimited
    max_reels_per_request: int
    is_active: bool = True
    created_at: datetime
    updated_at: datetime

    @computed_field
    @property
    def price_rub(self) -> float:
        """Price in rubles (price / 100)."""
        return self.price / 100

    class Config:
        from_attributes = True
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Base",
                "price": 99000,
                "price_rub": 990.0,
                "monthly_analyses": 100,
                "max_reels_per_request": 10,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }

from datetime import datetime

from pydantic import BaseModel, Field

from app.custom_enums import PlanType


class PlanModel(BaseModel):
    """Pydantic model for Plan database entity."""

    id: int = Field(description="Unique identifier for the plan")
    name: PlanType = Field(description="Name/type of the plan")
    price: int = Field(
        description="Price of the plan in cents or smallest currency unit"
    )
    monthly_analyses: int | None = Field(
        default=None,
        description="Number of monthly analyses allowed. None = Unlimited",
    )
    max_reels_per_request: int = Field(
        description="Maximum number of reels per request"
    )
    is_active: bool = Field(
        default=True, description="Whether the plan is active"
    )
    created_at: datetime = Field(description="When the plan was created")
    updated_at: datetime = Field(description="When the plan was last updated")

    class Config:
        from_attributes = True
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "id": 1,
                "name": "Base",
                "price": 999,
                "monthly_analyses": 100,
                "max_reels_per_request": 10,
                "is_active": True,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }

from pydantic import BaseModel, Field

from app.custom_enums import PlanType
from app.models import PlanModel


class CreatePlanRequestSchema(BaseModel):
    """Schema for creating a new plan."""

    name: PlanType = Field(description="Plan type (Test, Base, Unlimited)")
    price: int = Field(
        description="Price in cents/kopecks (e.g., 99000 = 990₽)"
    )
    monthly_analyses: int | None = Field(
        default=None,
        description="Monthly analyses limit. None = Unlimited",
    )
    max_reels_per_request: int = Field(description="Maximum reels per request")
    is_active: bool = Field(
        default=True, description="Whether the plan is active"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Base",
                "price": 99000,
                "monthly_analyses": 100,
                "max_reels_per_request": 10,
                "is_active": True,
            }
        }
    }


class UpdatePlanRequestSchema(BaseModel):
    """Schema for updating a plan. All fields are optional."""

    name: PlanType | None = Field(default=None, description="Plan type")
    price: int | None = Field(
        default=None, description="Price in cents/kopecks"
    )
    monthly_analyses: int | None = Field(
        default=None, description="Monthly analyses limit. None = Unlimited"
    )
    max_reels_per_request: int | None = Field(
        default=None, description="Maximum reels per request"
    )
    is_active: bool | None = Field(
        default=None, description="Whether the plan is active"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "price": 149000,
                "monthly_analyses": 150,
                "max_reels_per_request": 100,
                "is_active": True,
            }
        }
    }


class PlanResponseSchema(PlanModel):
    """Schema for single plan response."""


class ListPlanSchema(BaseModel):
    """Schema for list of plans response."""

    total: int = Field(description="Total number of plans")
    plans: list[PlanResponseSchema] = Field(
        description="List of available plans"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 3,
                "plans": [
                    {
                        "id": 1,
                        "name": "Test",
                        "price": 0,
                        "price_rub": 0.0,
                        "monthly_analyses": 5,
                        "max_reels_per_request": 3,
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    },
                    {
                        "id": 2,
                        "name": "Base",
                        "price": 99000,
                        "price_rub": 990.0,
                        "monthly_analyses": 100,
                        "max_reels_per_request": 10,
                        "is_active": True,
                        "created_at": "2024-01-01T00:00:00Z",
                        "updated_at": "2024-01-01T00:00:00Z",
                    },
                ],
            }
        }
    }

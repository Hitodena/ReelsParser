from datetime import datetime

from pydantic import BaseModel, Field


class ProfileModel(BaseModel):
    """Pydantic model for user profile data."""

    plan_name: str = Field(description="Current plan name")
    analyses_used: int = Field(
        description="Number of analyses used in current period"
    )
    monthly_analyses: int | None = Field(
        description="Monthly analyses limit (None = unlimited)"
    )
    remaining: int = Field(description="Remaining analyses (-1 for unlimited)")
    max_reels_per_request: int = Field(description="Maximum reels per request")
    period_start: datetime | None = Field(description="Billing period start")
    period_end: datetime | None = Field(description="Billing period end")
    has_paid_plan: bool = Field(
        description="Whether user has a paid plan (not Test)"
    )

    class Config:
        from_attributes = True
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "plan_name": "Base",
                "analyses_used": 5,
                "monthly_analyses": 100,
                "remaining": 95,
                "max_reels_per_request": 10,
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-02-01T00:00:00Z",
                "has_paid_plan": True,
            }
        }

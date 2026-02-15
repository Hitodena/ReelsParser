from datetime import datetime

from pydantic import BaseModel, Field


class TGUserModel(BaseModel):
    """Pydantic model for TGUser database entity."""

    id: int = Field(description="Unique identifier for the user")
    telegram_id: int = Field(description="Telegram user ID")
    plan_id: int = Field(description="ID of the user's current plan")
    analyses_used: int = Field(
        default=0, description="Number of analyses used in current period"
    )
    period_start: datetime = Field(
        description="Start of the current billing period"
    )
    period_end: datetime = Field(
        description="End of the current billing period"
    )
    created_at: datetime = Field(description="When the user was created")
    updated_at: datetime = Field(description="When the user was last updated")

    class Config:
        from_attributes = True
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "id": 1,
                "telegram_id": 123456789,
                "plan_id": 1,
                "analyses_used": 5,
                "period_start": "2024-01-01T00:00:00Z",
                "period_end": "2024-02-01T00:00:00Z",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }

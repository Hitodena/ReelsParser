from typing import Literal

from pydantic import BaseModel, Field

from app.models import TGUserModel


class LimitResponseSchema(BaseModel):
    """Schema for user limit check response."""

    can_parse: bool = Field(
        description="Whether the user can perform more analyses"
    )
    remaining: int = Field(
        description="Number of remaining analyses (-1 for unlimited)"
    )
    max_reels: int = Field(
        description="Maximum number of reels per request for user's plan"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "can_parse": True,
                "remaining": 50,
                "max_reels": 10,
            }
        }
    }


class IncrementResponseSchema(BaseModel):
    """Schema for usage increment response."""

    requests: int = Field(
        description="Total number of analyses used after increment"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "requests": 51,
            }
        }
    }


class RegisterTGUserSchema(BaseModel):
    """Schema for user registration response."""

    status: Literal["created", "exists"] = Field(
        description="Registration status - 'created' for new user, 'exists' for existing"
    )
    user: TGUserModel = Field(description="The user object with all details")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "created",
                "user": {
                    "id": 1,
                    "telegram_id": 123456789,
                    "plan_id": 1,
                    "analyses_used": 0,
                    "period_start": "2024-01-01T00:00:00Z",
                    "period_end": "2024-02-01T00:00:00Z",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z",
                },
            }
        }
    }

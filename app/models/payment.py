from datetime import datetime

from pydantic import BaseModel, Field


class PaymentModel(BaseModel):
    """Pydantic model for Payment database entity."""

    id: int = Field(description="Unique identifier for the payment")
    tg_user_id: int = Field(description="ID of the user who made the payment")
    invoice_id: str = Field(description="Unique invoice identifier")
    amount: int = Field(
        description="Payment amount in cents or smallest currency unit"
    )
    status: str = Field(
        description="Payment status (e.g., pending, completed, failed)"
    )
    created_at: datetime = Field(description="When the payment was created")
    updated_at: datetime = Field(
        description="When the payment was last updated"
    )

    class Config:
        from_attributes = True
        extra = "ignore"
        json_schema_extra = {
            "example": {
                "id": 1,
                "tg_user_id": 1,
                "invoice_id": "inv_123456789",
                "amount": 999,
                "status": "completed",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
            }
        }

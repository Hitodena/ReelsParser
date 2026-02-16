from pydantic import BaseModel, Field

from app.custom_enums import PlanType


class CreateRobokassaRequestSchema(BaseModel):
    """Schema for creating a Robokassa payment."""

    tg_id: int = Field(description="Telegram user ID")
    plan_type: PlanType = Field(description="Plan type to purchase")

    model_config = {
        "json_schema_extra": {
            "example": {
                "tg_id": 123456789,
                "plan_type": "Base",
            }
        }
    }


class CreateRobokassaResponseSchema(BaseModel):
    """Schema for Robokassa payment creation response."""

    payment_url: str = Field(description="URL to Robokassa payment page")
    invoice_id: str = Field(description="Unique invoice identifier")

    model_config = {
        "json_schema_extra": {
            "example": {
                "payment_url": "https://auth.robokassa.ru/Merchant/Index.aspx?MerchantLogin=...",
                "invoice_id": "INV_123456789_1708092300",
            }
        }
    }


class ResultRobokassaRequestSchema(BaseModel):
    """Schema for Robokassa ResultURL callback."""

    OutSum: str = Field(description="Payment amount")
    InvId: str = Field(description="Invoice ID")
    SignatureValue: str = Field(description="MD5 signature for verification")

    model_config = {
        "json_schema_extra": {
            "example": {
                "OutSum": "990.00",
                "InvId": "INV_123456789_1708092300",
                "SignatureValue": "a1b2c3d4e5f6...",
            }
        }
    }


class ResultRobokassaResponseSchema(BaseModel):
    """Schema for Robokassa ResultURL response."""

    status: str = Field(description="Response status")

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "OK",
            }
        }
    }

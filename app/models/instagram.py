from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class InstagramAuth(BaseModel):
    model_config = ConfigDict(from_attributes=True, extra="ignore")

    login: str = Field(description="Login to Instagram", min_length=2)
    password: str = Field(description="Password to Instagram", min_length=2)
    cookies: dict | None = Field(
        default=None, description="Saved cookies to Instagram"
    )
    last_used_at: datetime | None = Field(
        default=None,
        description="When was the account used last time in parsing",
    )
    valid: bool = Field(default=True, description="Is account valid or not")

    class Config:
        json_schema_extra = {
            "example": {
                "login": "username",
                "password": "your_password",
            }
        }

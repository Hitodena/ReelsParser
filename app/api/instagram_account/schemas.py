from pydantic import BaseModel, Field

from app.models import InstagramAuth


class AddAccountSchema(InstagramAuth): ...


class ResponseAccountSchema(InstagramAuth): ...


class ListAccountSchema(BaseModel):
    total: int = Field(description="Amount of accounts")
    accounts: list[AddAccountSchema] = Field(
        description="List of instagram accounts to parse"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "count": 1,
                "accounts": [
                    {
                        "login": "username",
                        "password": "your_password",
                        "cookies": {},
                        "last_used_at": None,
                    }
                ],
            }
        }


class UpdateValiditySchema(BaseModel):
    valid: bool = Field(description="Validity status of the account")


class DeleteAccountResponse(BaseModel):
    status: str = Field(description="Operation status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
            }
        }

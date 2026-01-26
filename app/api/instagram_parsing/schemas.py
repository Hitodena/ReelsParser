from pydantic import BaseModel, ConfigDict, Field


class ParseReelsSchema(BaseModel):
    target_username: str = Field(
        description="Target Instagram link to profile page from",
    )
    max_reels: int | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of reels to parse (null = all)",
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_username_link": "https://www.instagram.com/iamrigbycat",
                "max_reels": 100,
            }
        }
    )

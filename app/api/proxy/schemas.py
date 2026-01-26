from typing import Literal

from pydantic import BaseModel, Field


class ProxyAddSchema(BaseModel):
    host: str = Field(description="Proxy host")
    port: int = Field(description="Proxy port")
    username: str | None = Field(default=None, description="Proxy login")
    password: str | None = Field(default=None, description="Proxy password")
    protocol: Literal["http"] = Field(
        default="http", description="Proxy protocol (only http)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "host": "192.168.1.1",
                "port": "64602",
                "username": "admin",
                "password": "admin",
                "protocol": "http",
            }
        }


class ProxyResponseSchema(BaseModel):
    host: str = Field(description="Proxy host")
    port: int = Field(description="Proxy port")
    is_blocked: bool = Field(description="Proxy block flag")
    request_count: int = Field(description="Count of proxy connections")

    class Config:
        json_schema_extra = {
            "example": {
                "host": "192.168.1.1",
                "port": "64602",
                "is_blocked": "true",
                "request_count": "14",
            }
        }


class ProxyListSchema(BaseModel):
    total: int = Field(description="Total number of proxies")
    proxies: list[ProxyResponseSchema]

    class Config:
        json_schema_extra = {
            "example": {
                "total": 2,
                "proxies": [
                    {
                        "host": "192.168.1.1",
                        "port": "64602",
                        "is_blocked": "true",
                        "request_count": "14",
                    },
                    {
                        "host": "192.192,1,1",
                        "port": "64605",
                        "is_blocked": "false",
                        "request_count": "1",
                    },
                ],
            }
        }


class ProxyAddResponseSchema(BaseModel):
    status: str = Field(description="Operation status")
    proxy_id: str = Field(description="ID of the added proxy")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
                "proxy_id": "192.168.1.1:64602",
            }
        }


class ProxyDeleteResponseSchema(BaseModel):
    status: str = Field(description="Operation status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
            }
        }


class ProxyUnblockResponseSchema(BaseModel):
    status: str = Field(description="Operation status")

    class Config:
        json_schema_extra = {
            "example": {
                "status": "success",
            }
        }

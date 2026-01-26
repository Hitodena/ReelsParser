from datetime import datetime
from typing import Literal

from pydantic import BaseModel, computed_field


class ProxyModel(BaseModel):
    host: str
    port: int
    username: str | None = None
    password: str | None = None
    protocol: Literal["http"] = "http"

    last_used: datetime | None = None
    request_count: int = 0
    is_blocked: bool = False
    is_active: bool = True

    @computed_field
    @property
    def identifier(self) -> str:
        return f"{self.host}{self.port}"

    def to_playwright_proxy(self) -> dict:
        proxy = {"server": f"{self.protocol}://{self.host}:{self.port}"}
        if self.username and self.password:
            proxy["username"] = self.username
            proxy["password"] = self.password
        return proxy

    def to_httpx_proxy(self) -> str:
        if self.username:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

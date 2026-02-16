from typing import Literal

from pydantic import BaseModel, computed_field


class ProxyModel(BaseModel):
    """Proxy configuration model.

    State management (active/blocked) is handled by ProxyManager via Redis pools.
    """

    host: str
    port: int
    username: str | None = None
    password: str | None = None
    protocol: Literal["http"] = "http"

    @computed_field
    @property
    def identifier(self) -> str:
        """Unique identifier for the proxy."""
        return f"{self.host}:{self.port}"

    def to_playwright_proxy(self) -> dict:
        """Convert to Playwright proxy format."""
        proxy = {"server": f"{self.protocol}://{self.host}:{self.port}"}
        if self.username and self.password:
            proxy["username"] = self.username
            proxy["password"] = self.password
        return proxy

    def to_httpx_proxy(self) -> str:
        """Convert to httpx proxy format."""
        if self.username:
            return f"{self.protocol}://{self.username}:{self.password}@{self.host}:{self.port}"
        return f"{self.protocol}://{self.host}:{self.port}"

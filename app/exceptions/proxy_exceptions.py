from app.custom_enums import ProxyErrorsCodes


class ProxyError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: object,
    ) -> None:
        super().__init__(message)
        self.code = code


class InvalidProxyError(ProxyError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=ProxyErrorsCodes.INVALID_PROXY)


class NoProxyInPoolError(ProxyError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=ProxyErrorsCodes.NO_PROXY_IN_POOL)

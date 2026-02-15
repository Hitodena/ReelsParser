from app.custom_enums import ProxyErrorCodes


class ProxyError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: ProxyErrorCodes,
    ) -> None:
        super().__init__(message)
        self.code = code


class ProxyUnexpectedError(ProxyError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=ProxyErrorCodes.UNEXPECTED_ERROR)


class ProxyExhaustedError(ProxyError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=ProxyErrorCodes.EXHAUSTED_ERROR)

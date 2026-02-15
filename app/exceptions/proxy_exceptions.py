from app.custom_enums import ProxyErrorCodes


class ProxyError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: ProxyErrorCodes,
        partial_results: list[dict] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.partial_results = partial_results or []


class ProxyUnexpectedError(ProxyError):
    def __init__(
        self, message: str, *, partial_results: list[dict] | None = None
    ) -> None:
        super().__init__(
            message,
            code=ProxyErrorCodes.UNEXPECTED_ERROR,
            partial_results=partial_results,
        )


class ProxyTooManyAttemptsError(ProxyError):
    def __init__(
        self, message: str, *, partial_results: list[dict] | None = None
    ) -> None:
        super().__init__(
            message,
            code=ProxyErrorCodes.TOO_MANY_ATTEMPTS_ERROR,
            partial_results=partial_results,
        )


class ProxyForbiddenError(ProxyError):
    def __init__(
        self, message: str, *, partial_results: list[dict] | None = None
    ) -> None:
        super().__init__(
            message,
            code=ProxyErrorCodes.FORBIDDEN_ERROR,
            partial_results=partial_results,
        )

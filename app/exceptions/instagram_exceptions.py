from app.custom_enums import (
    InstagramErrorCodes,
    NetworkErrorCodes,
)

RETRYABLE = {
    NetworkErrorCodes.TIMEOUT,
    NetworkErrorCodes.CONNECTION_ERROR,
}


class InstagramParserError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: object,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.retryable = code in RETRYABLE


class AuthUnexpectedError(InstagramParserError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=InstagramErrorCodes.UNEXPECTED_ERROR)


class AuthCredentialsError(InstagramParserError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=InstagramErrorCodes.INVALID_CREDENTIALS)


class NetworkError(InstagramParserError):
    def __init__(self, message: str, code: NetworkErrorCodes) -> None:
        super().__init__(message, code=code)

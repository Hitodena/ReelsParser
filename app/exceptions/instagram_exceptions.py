from app.custom_enums import (
    InstagramErrorCodes,
)


class InstagramParserError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: object,
    ) -> None:
        super().__init__(message)
        self.code = code


class AuthUnexpectedError(InstagramParserError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=InstagramErrorCodes.UNEXPECTED_ERROR)


class AuthCredentialsError(InstagramParserError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code=InstagramErrorCodes.INVALID_CREDENTIALS)


class UserPrivateError(InstagramParserError):
    def __init__(self, message: str = "This account is private") -> None:
        super().__init__(message, code=InstagramErrorCodes.USER_PRIVATE)


class UserNotFoundError(InstagramParserError):
    def __init__(
        self, message: str = "Sorry, this page isn't available."
    ) -> None:
        super().__init__(message, code=InstagramErrorCodes.USER_NOT_FOUND)

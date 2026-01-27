from enum import StrEnum


class InstagramErrorCodes(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    UNEXPECTED_ERROR = "unexpected_error"
    USER_PRIVATE = "user_private"
    USER_NOT_FOUND = "user_not_found"

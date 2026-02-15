from enum import StrEnum


class InstagramErrorCodes(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    UNEXPECTED_ERROR = "parser_unexpected_error"
    USER_PRIVATE = "user_private"
    USER_NOT_FOUND = "user_not_found"


class ProxyErrorCodes(StrEnum):
    UNEXPECTED_ERROR = "proxy_unexpected_error"
    EXHAUSTED_ERROR = "proxy_exhausted"

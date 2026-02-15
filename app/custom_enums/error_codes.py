from enum import StrEnum


class InstagramErrorCodes(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    UNEXPECTED_ERROR = "parser_unexpected_error"
    USER_PRIVATE = "user_private"
    USER_NOT_FOUND = "user_not_found"


class ProxyErrorCodes(StrEnum):
    UNEXPECTED_ERROR = "proxy_unexpected_error"
    TOO_MANY_ATTEMPTS_ERROR = "proxy_too_many_attempts"
    FORBIDDEN_ERROR = "proxy_forbidden"

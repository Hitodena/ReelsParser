from .instagram_exceptions import (
    AuthCredentialsError,
    AuthUnexpectedError,
    InstagramParserError,
    UserNotFoundError,
    UserPrivateError,
)
from .proxy_exceptions import (
    ProxyError,
    ProxyForbiddenError,
    ProxyTooManyAttemptsError,
    ProxyUnexpectedError,
)

__all__ = [
    "AuthCredentialsError",
    "InstagramParserError",
    "AuthUnexpectedError",
    "UserNotFoundError",
    "UserPrivateError",
    "ProxyError",
    "ProxyForbiddenError",
    "ProxyTooManyAttemptsError",
    "ProxyUnexpectedError",
]

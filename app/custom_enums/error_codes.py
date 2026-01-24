from enum import StrEnum


class NetworkErrorCodes(StrEnum):
    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"


class InstagramErrorCodes(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    UNEXPECTED_ERROR = "unexpected_error"


class ProxyErrorsCodes(StrEnum):
    INVALID_PROXY = "invalid_proxy"
    NO_PROXY_IN_POOL = "no_proxy_in_pool"

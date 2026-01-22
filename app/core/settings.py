from pydantic import BaseModel, Field


class Logs(BaseModel):
    """Logging configuration"""

    file_log_level: str = Field(
        default="INFO", description="Log level for file logging"
    )


class Retries(BaseModel):
    """Retry configuration"""

    max_connection_attempts: int = Field(
        default=3, description="Maximum number of connection retries"
    )
    max_proxy_get_attempts: int = Field(
        default=3, description="Maximum number of proxy retrieval retries"
    )


class Timeouts(BaseModel):
    """Timeout configuration"""

    connection_timeout: int = Field(
        default=30,
        description="Timeout for establishing a connection (in seconds)",
    )


class Network(BaseModel):
    """Network configuration"""

    sleep_between_actions: int = Field(
        default=2, description="Sleep time between actions (in seconds)"
    )
    sleep_between_requests_min: float = Field(
        default=0.5,
        description="Minimum sleep time between requests (in seconds)",
    )
    sleep_between_requests_max: float = Field(
        default=2,
        description="Maximum sleep time between requests (in seconds)",
    )


class Parsing(BaseModel):
    """Parsing configuration"""

    instagram_reels_url: str = Field(
        default="/reels",
        description="URL for the reels page",
    )
    api_instagram_reels_url: str = Field(
        default="https://www.instagram.com/graphql/query",
        description="GraphQL Reels URL for Instagram",
    )
    instagram_login_url: str = Field(
        default="https://www.instagram.com/accounts/login/",
        description="Login Instagram URL",
    )


class Dentifiers(BaseModel):
    """Identities for selectors and requests to Instagram"""

    reels_graph_ql_identity: str = Field(
        default="PolarisProfileReelsTabContentQuery",
        description="Dentifier for reels API graphql, X-FB-Friendly-Name: PolarisProfileReelsTabContentQuery_connection in request headers",
    )
    graph_ql_identity: str = Field(
        default="graphql/query", description="GraphQL request dentifier"
    )

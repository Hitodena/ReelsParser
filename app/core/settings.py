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
    max_retries: int = Field(
        default=3, description="Maximum number of retries for fetching reels"
    )


class Timeouts(BaseModel):
    """Timeout configuration"""

    connection_timeout: int = Field(
        default=30,
        description="Timeout for establishing a connection (in seconds)",
    )
    timeout_element: int = Field(
        default=10, description="Timeout for selecting a element (in seconds)"
    )
    timeout_for_element_state: int = Field(
        default=4, description="Timeout for element state (in seconds)"
    )


class Network(BaseModel):
    """Network configuration"""

    sleep_between_actions: float = Field(
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
    concurrent_limit: int = Field(
        default=5, description="Maximum concurrent network connections"
    )
    backoff_factor: float = Field(
        default=2, description="Backoff factor for retries "
    )
    rate_limit_wait_base: float = Field(
        default=5,
        description="Base wait time for rate limit backoff (in seconds)",
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
    instagram_url: str = Field(
        default="https://www.instagram.com/",
        description="URL to check if login after cookies/auth",
    )


class Identifiers(BaseModel):
    """Identities for selectors and requests to Instagram"""

    reels_graph_ql_identity: str = Field(
        default="PolarisProfileReelsTabContentQuery",
        description="Dentifier for reels API graphql, X-FB-Friendly-Name: PolarisProfileReelsTabContentQuery_connection in request headers",
    )
    graph_ql_identity: str = Field(
        default="graphql/query", description="GraphQL request dentifier"
    )
    old_field_username_selector: str = Field(
        default="Phone number, username, or email",
        description="Selector for username on old page",
    )
    old_field_password_selector: str = Field(
        default="Password",
        description="Selector for password on old page",
    )
    old_field_login_selector: str = Field(
        default="Log in",
        description="Selector for log in on old page",
    )
    new_field_username_selector: str = Field(
        default="Mobile number, username or email",
        description="Selector for username on new page",
    )
    new_field_password_selector: str = Field(
        default="Password",
        description="Selector for password on new page",
    )
    new_field_login_selector: str = Field(
        default="Log in",
        description="Selector for log in on old page",
    )
    error_texts: list[str] = Field(
        default=[
            "Sorry, your password was incorrect",
            "The login information you entered is incorrect",
            "We couldn't connect to Instagram",
        ],
        description="Error messages for login page",
    )
    continue_button_selector: str = Field(
        default="Continue", description="Contunue button after login"
    )
    save_button_selector: str = Field(
        default="Save info", description="Save button after login"
    )
    additional_password_selector: str = Field(
        default="Password",
        description="Selector for additional modal password field",
    )
    additional_login_selector: str = Field(
        default="Log In",
        description="Selector for additional login button",
    )

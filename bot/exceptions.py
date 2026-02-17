class BotAPIError(Exception):
    """Base exception for bot API errors"""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class NoAccountsForParsingError(BotAPIError):
    """No account available for parsing"""

    def __init__(self):
        super().__init__(
            "Нету аккаунтов для парсинга, обратитесь к админу.",
            404,
        )


class PlanNotFound(BotAPIError):
    """No plan available for creating"""

    def __init__(self):
        super().__init__(
            "Нету планов для пользователей, обратитесь к админу.",
            404,
        )


class UserNotFoundError(BotAPIError):
    """User not registered in system"""

    def __init__(self):
        super().__init__("Вы не зарегистрированы. Введите /start", 404)


class PrivateAccountError(BotAPIError):
    """Instagram account is private"""

    def __init__(self, username: str):
        super().__init__(f"Аккаунт @{username} приватный", 403)


class UnexpectedError(BotAPIError):
    """Any other errors"""

    def __init__(self):
        super().__init__("Неизвестная ошибка", 500)


class AlreadyHasPlanError(BotAPIError):
    """User already has an active paid plan"""

    def __init__(self, message: str):
        super().__init__(message, 400)

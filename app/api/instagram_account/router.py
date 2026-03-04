"""Instagram Account API router for managing Instagram accounts."""

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse

from app.api.deps import (
    get_browser,
    get_db,
    get_orchestrator,
    get_proxy_manager,
)
from app.db.dao import InstagramAccountDAO
from app.exceptions import AuthCredentialsError, AuthUnexpectedError
from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    InstagramOrchestrator,
    ProxyManager,
)

from .schemas import (
    AddAccountSchema,
    DeleteAccountResponse,
    ListAccountSchema,
    ResponseAccountSchema,
    UpdateValiditySchema,
)

account_router = APIRouter(prefix="/accounts", tags=["Instagram Accounts"])


def get_latest_screenshot() -> dict[str, Any] | None:
    """Get the latest screenshot file info.

    Returns:
        dict with filename and base64 content, or None if no screenshot exists
    """
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        return None

    screenshots = list(logs_dir.glob("auth_error_*.png"))
    if not screenshots:
        return None

    latest = max(screenshots, key=lambda p: p.stat().st_mtime)
    try:
        import base64

        return {
            "filename": latest.name,
            "data": base64.b64encode(latest.read_bytes()).decode("utf-8"),
        }
    except Exception:
        return None


@account_router.get(
    "",
    response_model=ListAccountSchema,
    status_code=status.HTTP_200_OK,
    summary="List all Instagram accounts",
    description="Retrieve a list of all Instagram accounts with their basic information.",
    responses={
        200: {"description": "Accounts retrieved successfully"},
        404: {"description": "No accounts found"},
        500: {"description": "Internal Server Error"},
    },
)
async def list_accounts(
    db: DatabaseSessionManager = Depends(get_db),
) -> ListAccountSchema:
    """
    Retrieves a list of all Instagram accounts.

    Args:
        db: Database session manager dependency.

    Returns:
        ListAccountSchema: List of accounts with total count.

    Raises:
        HTTPException: 404 if no accounts exist.

    Example:
        GET /api/accounts
        Response: {
            "total": 2,
            "accounts": [
                {
                    "login": "user1",
                    "password": "pass1",
                    "cookies": {},
                    "last_used_at": "2024-01-01T12:00:00Z"
                }
            ]
        }
    """
    async with db.session() as session:
        accounts = await InstagramAccountDAO.get_all(session)

    if accounts is None:
        raise HTTPException(404, "No accounts found")

    account_summaries = [
        AddAccountSchema.model_validate(acc) for acc in accounts
    ]

    return ListAccountSchema(total=len(accounts), accounts=account_summaries)


@account_router.get(
    "/{login}",
    response_model=ResponseAccountSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Instagram account details",
    description="Retrieve detailed information about a specific Instagram account by login.",
    responses={
        200: {"description": "Account retrieved successfully"},
        404: {"description": "Account not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_account(
    login: str,
    db: DatabaseSessionManager = Depends(get_db),
) -> ResponseAccountSchema:
    """
    Retrieves detailed information about a specific Instagram account.

    Args:
        login (str): The login of the Instagram account.
        db: Database session manager dependency.

    Returns:
        ResponseAccountSchema: Detailed account information.

    Raises:
        HTTPException: 404 if account not found.

    Example:
        GET /api/accounts/user1
        Response: {
            "login": "user1",
            "password": "encrypted_password",
            "cookies": {"sessionid": "abc123"},
            "last_used_at": "2024-01-01T12:00:00Z"
        }
    """
    async with db.session() as session:
        account = await InstagramAccountDAO.get_by_login(session, login)

    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Account '{login}' not found",
        )

    return ResponseAccountSchema.model_validate(account)


@account_router.post(
    "",
    response_model=ResponseAccountSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add Instagram account",
    description=(
        "Add a new Instagram account by logging in and extracting credentials. "
        "The account will be stored in the database for future use."
    ),
    responses={
        201: {"description": "Account added successfully"},
        400: {"description": "Account already exists or invalid credentials"},
        500: {"description": "Internal Server Error"},
    },
)
async def add_account(
    data: AddAccountSchema,
    db: DatabaseSessionManager = Depends(get_db),
    orchestrator: InstagramOrchestrator = Depends(get_orchestrator),
    browser: BrowserManager = Depends(get_browser),
    proxy_manager: ProxyManager = Depends(get_proxy_manager),
) -> ResponseAccountSchema:
    """
    Add a new Instagram account with automatic login verification.

    **Workflow:**
    1. Check if account already exists in database
    2. Get least used proxy for login
    3. Login via Playwright with provided credentials
    4. Extract session cookies
    5. Save account to database

    Args:
        data: Account credentials (login and password).
        db: Database session manager dependency.
        orchestrator: Instagram orchestrator for login operations.
        browser: Browser manager for Playwright context.
        proxy_manager: Proxy manager for getting proxies.

    Returns:
        ResponseAccountSchema: Created account with all details.

    Raises:
        HTTPException: 400 if account already exists.
        HTTPException: 500 if login fails.

    Example:
        POST /api/accounts
        Body: {
            "login": "newuser",
            "password": "securepassword"
        }
        Response: {
            "login": "newuser",
            "password": "securepassword",
            "cookies": {"sessionid": "abc123"},
            "last_used_at": null
        }
    """
    try:
        async with db.session() as session:
            existing = await InstagramAccountDAO.get_by_login(
                session, data.login
            )
        if existing:
            raise HTTPException(400, f"Account '{data.login}' already exists")

        proxy_formatted = None
        proxy = await proxy_manager.get_least_used()
        if proxy:
            proxy_formatted = proxy.to_playwright_proxy()

        async with browser.context(proxy=proxy_formatted) as (page, ctx):
            cookies = await orchestrator.check_account_login(page, ctx, data)

        async with db.session() as session:
            account = await InstagramAccountDAO.add(
                session,
                login=data.login,
                password=data.password,
                cookies=cookies,
                valid=True,
            )

        return ResponseAccountSchema.model_validate(account)
    except HTTPException:
        raise
    except AuthCredentialsError as exc:
        screenshot = get_latest_screenshot()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Failed to add '{data.login}' - invalid credentials: {exc}",
                "screenshot": screenshot,
            },
        )
    except AuthUnexpectedError as exc:
        screenshot = get_latest_screenshot()
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "message": f"Failed to add '{data.login}' - unexpected error: {exc}",
                "screenshot": screenshot,
            },
        )


@account_router.get(
    "/screenshots/latest",
    summary="Get latest auth screenshot",
    description="Download the latest authentication error screenshot.",
)
async def get_latest_screenshot_endpoint():
    """Get the latest screenshot file for debugging login issues."""
    logs_dir = Path("./logs")
    if not logs_dir.exists():
        raise HTTPException(404, "No screenshot found")

    screenshots = list(logs_dir.glob("auth_error_*.png"))
    if not screenshots:
        raise HTTPException(404, "No screenshot found")

    latest = max(screenshots, key=lambda p: p.stat().st_mtime)
    return FileResponse(latest, media_type="image/png", filename=latest.name)


@account_router.delete(
    "/{login}",
    response_model=DeleteAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Instagram account",
    description="Delete a specific Instagram account by login.",
    responses={
        200: {"description": "Account deleted successfully"},
        404: {"description": "Account not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def delete_account(
    login: str,
    db: DatabaseSessionManager = Depends(get_db),
) -> DeleteAccountResponse:
    """
    Deletes a specific Instagram account by login.

    Args:
        login (str): The login of the Instagram account to delete.
        db: Database session manager dependency.

    Returns:
        DeleteAccountResponse: Response containing the deletion status.

    Raises:
        HTTPException: 404 if account not found.

    Example:
        DELETE /api/accounts/user1
        Response: {"status": "success"}
    """
    try:
        async with db.session() as session:
            account = await InstagramAccountDAO.delete_by_login(session, login)
        if not account:
            raise HTTPException(404, f"Account '{login}' not found")
        return DeleteAccountResponse(status="success")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Failed to delete account: {exc}")


@account_router.patch(
    "/{login}/validity",
    response_model=ResponseAccountSchema,
    status_code=status.HTTP_200_OK,
    summary="Update Instagram account validity",
    description="Update the validity status of a specific Instagram account.",
    responses={
        200: {"description": "Account validity updated successfully"},
        404: {"description": "Account not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def update_account_validity(
    login: str,
    data: UpdateValiditySchema,
    db: DatabaseSessionManager = Depends(get_db),
) -> ResponseAccountSchema:
    """
    Updates the validity status of a specific Instagram account.

    Valid accounts are used for parsing, invalid accounts are skipped.
    Use this to manually mark accounts as valid/invalid.

    Args:
        login (str): The login of the Instagram account.
        data (UpdateValiditySchema): The validity data to update.
        db: Database session manager dependency.

    Returns:
        ResponseAccountSchema: Updated account information.

    Raises:
        HTTPException: 404 if account not found.

    Example:
        PATCH /api/accounts/user1/validity
        Body: {"valid": true}
        Response: {
            "login": "user1",
            "password": "encrypted",
            "cookies": {},
            "last_used_at": "2024-01-01T12:00:00Z"
        }
    """
    try:
        async with db.session() as session:
            account = await InstagramAccountDAO.update_validity(
                session, login, data.valid
            )
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account '{login}' not found",
            )
        return ResponseAccountSchema.model_validate(account)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update account validity: {exc}",
        )

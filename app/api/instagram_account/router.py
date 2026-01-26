from fastapi import APIRouter, Depends, HTTPException, status

from app.db.dao import InstagramAccountDAO
from app.services import (
    BrowserManager,
    DatabaseSessionManager,
    InstagramOrchestrator,
)

from ..deps import get_browser, get_db, get_orchestrator
from .schemas import (
    AddAccountSchema,
    DeleteAccountResponse,
    ListAccountSchema,
    ResponseAccountSchema,
)

account_router = APIRouter(prefix="/accounts", tags=["Instagram Accounts"])


@account_router.get(
    "/list",
    response_model=ListAccountSchema,
    status_code=status.HTTP_200_OK,
    summary="List all Instagram accounts",
    description="Retrieve a list of all Instagram accounts with their basic information.",
    responses={
        200: {"description": "Accounts retrieved"},
        500: {"description": "Internal Server Error"},
    },
)
async def list_accounts(db: DatabaseSessionManager = Depends(get_db)):
    """
    Retrieves a list of all Instagram accounts.

    Args:
        db: Database session dependency.

    Returns:
        ListAccountSchema: List of accounts.
    """
    async with db.session() as session:
        accounts = await InstagramAccountDAO.get_all(session)
        if accounts is None:
            accounts = []

        account_summaries = [
            AddAccountSchema.model_validate(acc) for acc in accounts
        ]

        return ListAccountSchema(
            total=len(accounts), accounts=account_summaries
        )


@account_router.get(
    "/{login}",
    response_model=ResponseAccountSchema,
    status_code=status.HTTP_200_OK,
    summary="Get Instagram account details",
    description="Retrieve detailed information about a specific Instagram account by login.",
    responses={
        200: {"description": "Account retrieved"},
        404: {"description": "Not Found - Account not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_account(
    login: str, db: DatabaseSessionManager = Depends(get_db)
):
    """
    Retrieves detailed information about a specific Instagram account by login.

    Args:
        login (str): The login of the Instagram account.
        db: Database session dependency.

    Returns:
        ResponseAccountSchema: Detailed account information.

    Raises:
        HTTPException: If the account is not found.
    """
    async with db.session() as session:
        account = await InstagramAccountDAO.get_by_login(session, login)

        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Account not found",
            )

        return ResponseAccountSchema.model_validate(account)


@account_router.delete(
    "/{login}",
    response_model=DeleteAccountResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Instagram account",
    description="Delete a specific Instagram account by login.",
    responses={
        200: {"description": "Account deleted successfully"},
        404: {"description": "Not Found - Account not found"},
        500: {
            "description": "Internal Server Error - Failed to delete account"
        },
    },
)
async def delete_account(
    login: str, db: DatabaseSessionManager = Depends(get_db)
) -> DeleteAccountResponse:
    """
    Deletes a specific Instagram account by login.

    Args:
        login (str): The login of the Instagram account to delete.
        db: Database session dependency.

    Returns:
        DeleteAccountResponse: Response containing the status of the deletion.
    """
    try:
        async with db.session() as session:
            account = await InstagramAccountDAO.delete_by_login(session, login)
            if not account:
                raise HTTPException(404, "Account not found")
        return DeleteAccountResponse(status="success")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(500, f"Failed to delete account: {exc}")


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
        201: {
            "description": "Account added successfully",
        },
        400: {
            "description": "Bad Request - Account already exists or invalid credentials",
        },
        500: {"description": "Internal Server Error"},
    },
)
async def add_account(
    data: AddAccountSchema,
    db: DatabaseSessionManager = Depends(get_db),
    orchestrator: InstagramOrchestrator = Depends(get_orchestrator),
    browser: BrowserManager = Depends(get_browser),
):
    """
    Add new Instagram account.

    **Workflow:**
    1. Login via Playwright with provided credentials
    2. Extract session cookies
    3. Validate login success
    4. Save account to database

    Args:
        data: Account credentials (login and password).

    Returns:
        AddAccountResponse: Success status with account ID and username.

    Raises:
        HTTPException 400: If account already exists or login fails.
        HTTPException 500: For unexpected errors.
    """
    try:
        async with db.session() as session:
            # Check if account exists
            existing = await InstagramAccountDAO.get_by_login(
                session, data.login
            )
            if existing:
                raise HTTPException(400, "Account already exists")

        # Get browser context
        async with browser.context() as (page, ctx):
            # Logging in and extracting
            cookies = await orchestrator.check_account_login(page, ctx, data)

        # Save into DB
        async with db.session() as session:
            # Create DB Account
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
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add account: {exc}",
        )

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_db
from app.custom_enums import PlanType
from app.db.dao import PlanDAO, TGUserDAO
from app.models import TGUserModel
from app.services import DatabaseSessionManager

from .schemas import (
    IncrementResponseSchema,
    LimitResponseSchema,
    ProfileResponseSchema,
    RegisterTGUserSchema,
)

user_router = APIRouter(prefix="/users", tags=["Users"])


@user_router.get(
    "/{tg_id}/limit",
    response_model=LimitResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Check user parsing limit",
    description=(
        "Check if a Telegram user can perform more analyses and get "
        "remaining analyses count and max reels per request."
    ),
    responses={
        200: {"description": "Limit information retrieved"},
        404: {"description": "User not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def check_limit(
    tg_id: int,
    db: DatabaseSessionManager = Depends(get_db),
) -> LimitResponseSchema:
    """
    Check user's parsing limit and remaining analyses.

    Args:
        tg_id (int): Telegram user ID.
        db: Database session manager dependency.

    Returns:
        LimitResponseSchema: Contains can_parse, remaining, and max_reels.

    Raises:
        HTTPException: 404 if user not found.

    Example:
        GET /api/users/123456789/limit
        Response: {
            "can_parse": true,
            "remaining": 50,
            "max_reels": 10
        }
    """
    async with db.session() as session:
        can_parse, remaining, max_reels = await TGUserDAO.check_limit(
            tg_id, session
        )
        await session.commit()

    if remaining == 0 and not can_parse:
        # Check if user exists by verifying max_reels is 0 (user not found)
        if max_reels == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

    return LimitResponseSchema(
        can_parse=can_parse,
        remaining=remaining,
        max_reels=max_reels,
    )


@user_router.post(
    "/{tg_id}/increment",
    response_model=IncrementResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Increment user usage count",
    description="Increment the analysis usage count for a Telegram user after successful parsing.",
    responses={
        200: {"description": "Usage incremented successfully"},
        404: {"description": "User not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def increment_usage(
    tg_id: int,
    db: DatabaseSessionManager = Depends(get_db),
) -> IncrementResponseSchema:
    """
    Increment user's usage count.

    Args:
        tg_id (int): Telegram user ID.
        db: Database session manager dependency.

    Returns:
        IncrementResponseSchema: Contains the new total requests count.

    Raises:
        HTTPException: 404 if user not found.

    Example:
        POST /api/users/123456789/increment
        Response: {"requests": 51}
    """
    async with db.session() as session:
        requests = await TGUserDAO.increment_usage(tg_id, session)
        await session.commit()

    if requests == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return IncrementResponseSchema(requests=requests)


@user_router.post(
    "/{tg_id}/register",
    response_model=RegisterTGUserSchema,
    status_code=status.HTTP_200_OK,
    summary="Register a new Telegram user",
    description=(
        "Register a new Telegram user with the TEST plan. "
        "If user already exists, returns existing user with 'exists' status."
    ),
    responses={
        200: {"description": "User registered or already exists"},
        404: {
            "description": "Test plan not found (system configuration error)"
        },
        500: {"description": "Internal Server Error"},
    },
)
async def register_user(
    tg_id: int,
    db: DatabaseSessionManager = Depends(get_db),
) -> RegisterTGUserSchema:
    """
    Register a new Telegram user with TEST plan.

    If the user already exists, returns the existing user with status 'exists'.
    New users are created with the TEST plan and a 30-day billing period.

    Args:
        tg_id (int): Telegram user ID.
        db: Database session manager dependency.

    Returns:
        RegisterTGUserSchema: Contains status and user details.

    Raises:
        HTTPException: 404 if TEST plan not found.

    Example:
        POST /api/users/123456789/register
        Response: {
            "status": "created",
            "user": {...}
        }
    """
    async with db.session() as session:
        # Check if user already exists
        existing_user = await TGUserDAO.get_by_telegram_id(tg_id, session)
        if existing_user:
            return RegisterTGUserSchema(status="exists", user=existing_user)

        # Get TEST plan for new users
        test_plan = await PlanDAO.get_by_active_type(PlanType.TEST, session)
        if not test_plan:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test plan not found. Please contact support.",
            )

        # Create new user with TEST plan
        now = datetime.now(timezone.utc)
        new_user = await TGUserDAO.add(
            session,
            telegram_id=tg_id,
            plan_id=test_plan.id,
            analyses_used=0,
            period_start=now,
            period_end=now + timedelta(days=30),
        )

        return RegisterTGUserSchema(
            status="created",
            user=TGUserModel.model_validate(new_user),
        )


@user_router.get(
    "/{tg_id}/profile",
    response_model=ProfileResponseSchema,
    status_code=status.HTTP_200_OK,
    summary="Get user profile",
    description="Get user's current plan, usage, and billing period information.",
    responses={
        200: {"description": "Profile information retrieved"},
        404: {"description": "User not found"},
        500: {"description": "Internal Server Error"},
    },
)
async def get_profile(
    tg_id: int,
    db: DatabaseSessionManager = Depends(get_db),
) -> ProfileResponseSchema:
    """
    Get user profile with plan and usage information.

    Args:
        tg_id (int): Telegram user ID.
        db: Database session manager dependency.

    Returns:
        ProfileResponseSchema: User profile with plan details.

    Raises:
        HTTPException: 404 if user not found.
    """
    async with db.session() as session:
        profile = await TGUserDAO.get_profile(tg_id, session)

        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        return ProfileResponseSchema.model_validate(profile)

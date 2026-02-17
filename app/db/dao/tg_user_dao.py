from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.custom_enums import PlanType
from app.models import ProfileModel, TGUserModel

from ..models import TGUser
from .base_dao import BaseDAO


class TGUserDAO(BaseDAO[TGUser]):
    model = TGUser

    @classmethod
    async def get_by_telegram_id(
        cls, tg_id: int, session: AsyncSession
    ) -> TGUserModel | None:
        """
        Retrieves a user by their Telegram ID.

        Args:
            tg_id (int): The Telegram ID of the user to retrieve.
            session (AsyncSession): The database session to use for the query.

        Returns:
            TGUserModel | None: The matching user if found, otherwise None.
        """
        logger.bind(model=cls.model, telegram_id=tg_id).info(
            "Getting user by telegram id"
        )
        stmt = select(cls.model).where(cls.model.telegram_id == tg_id)
        try:
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if not user:
                logger.bind(model=cls.model, telegram_id=tg_id).warning(
                    "No user found by telegram id"
                )
                return None
            logger.bind(model=cls.model, telegram_id=tg_id).info(
                "Found user by telegram id"
            )
            return TGUserModel.model_validate(user)
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, telegram_id=tg_id
            ).exception("Failed to get user by telegram id")
            raise

    @classmethod
    async def check_and_reset_period(
        cls, user: TGUser, session: AsyncSession
    ) -> None:
        """
        Checks if the user's billing period has expired and resets it if necessary.

        Args:
            user (TGUser): The user to check and potentially reset.
            session (AsyncSession): The database session to use for the update.
        """
        logger.bind(model=cls.model, telegram_id=user.telegram_id).info(
            "Checking and resetting period for user"
        )
        now = datetime.now(timezone.utc)
        if now > user.period_end:
            user.analyses_used = 0
            user.period_start = now
            user.period_end = user.period_start + timedelta(days=30)
            await session.flush()
            logger.bind(model=cls.model, telegram_id=user.telegram_id).info(
                "Period reset for user"
            )

    @classmethod
    async def check_limit(
        cls, tg_id: int, session: AsyncSession
    ) -> tuple[bool, int, int]:
        """
        Checks if the user has remaining analyses in their current billing period.

        Args:
            tg_id (int): The Telegram ID of the user to check.
            session (AsyncSession): The database session to use for the query.

        Returns:
            tuple[bool, int, int]: A tuple containing:
                - bool: True if the user can perform more analyses, False otherwise.
                - int: Number of remaining analyses (-1 for unlimited).
                - int: Maximum reels per request for the user's plan.
        """
        logger.bind(model=cls.model, telegram_id=tg_id).info(
            "Checking usage limit for user"
        )
        try:
            # Get the full SQLAlchemy model for period check
            stmt = select(cls.model).where(cls.model.telegram_id == tg_id)
            result = await session.execute(stmt)
            db_user = result.scalar_one_or_none()

            if not db_user:
                logger.bind(model=cls.model, telegram_id=tg_id).warning(
                    "User not found for limit check"
                )
                return False, 0, 0

            await cls.check_and_reset_period(db_user, session)

            max_reels = db_user.plan.max_reels_per_request

            if db_user.plan.monthly_analyses is None:  # Unlimited
                logger.bind(model=cls.model, telegram_id=tg_id).info(
                    "User has unlimited plan"
                )
                return True, -1, max_reels

            remaining = db_user.plan.monthly_analyses - db_user.analyses_used
            logger.bind(
                model=cls.model, telegram_id=tg_id, remaining=remaining
            ).info("Checked usage limit for user")
            return remaining > 0, remaining, max_reels
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, telegram_id=tg_id
            ).exception("Failed to check usage limit")
            raise

    @classmethod
    async def increment_usage(cls, tg_id: int, session: AsyncSession) -> int:
        """
        Increments the usage count for a user.

        Args:
            tg_id (int): The Telegram ID of the user to increment usage for.
            session (AsyncSession): The database session to use for the update.

        Returns:
            int: The new analyses_used count after increment. Returns 0 if user not found.
        """
        logger.bind(model=cls.model, telegram_id=tg_id).info(
            "Incrementing usage for user"
        )
        try:
            stmt = select(cls.model).where(cls.model.telegram_id == tg_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.analyses_used += 1
                await session.flush()
                logger.bind(
                    model=cls.model,
                    telegram_id=tg_id,
                    analyses_used=user.analyses_used,
                ).info("Incremented usage for user")
                return user.analyses_used
            else:
                logger.bind(model=cls.model, telegram_id=tg_id).warning(
                    "User not found for usage increment"
                )
                return 0
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, telegram_id=tg_id
            ).exception("Failed to increment usage")
            raise

    @classmethod
    async def upgrade_plan(
        cls, tg_id: int, new_plan_id: int, session: AsyncSession
    ) -> TGUserModel | None:
        """
        Upgrades a user's plan to a new plan.

        Args:
            tg_id (int): The Telegram ID of the user to upgrade.
            new_plan_id (int): The ID of the new plan.
            session (AsyncSession): The database session to use for the update.

        Returns:
            TGUserModel | None: The updated user if successful, otherwise None.
        """
        logger.bind(
            model=cls.model, telegram_id=tg_id, new_plan_id=new_plan_id
        ).info("Upgrading plan for user")
        try:
            stmt = select(cls.model).where(cls.model.telegram_id == tg_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user:
                user.plan_id = new_plan_id
                user.analyses_used = 0
                user.period_start = datetime.now(timezone.utc)
                user.period_end = user.period_start + timedelta(days=30)
                await session.flush()
                await session.refresh(user)
                logger.bind(
                    model=cls.model, telegram_id=tg_id, new_plan_id=new_plan_id
                ).info("Upgraded plan for user")
                return TGUserModel.model_validate(user)
            logger.bind(
                model=cls.model, telegram_id=tg_id, new_plan_id=new_plan_id
            ).warning("User not found for plan upgrade")
            return None
        except Exception as exc:
            logger.bind(
                error_message=exc,
                model=cls.model,
                telegram_id=tg_id,
                new_plan_id=new_plan_id,
            ).exception("Failed to upgrade plan")
            raise

    @classmethod
    async def get_profile(
        cls, tg_id: int, session: AsyncSession
    ) -> ProfileModel | None:
        """
        Get user profile with plan and usage information.

        Args:
            tg_id (int): The Telegram ID of the user.
            session (AsyncSession): The database session.

        Returns:
            ProfileModel | None: Profile data if user found, otherwise None.
        """
        logger.bind(model=cls.model, telegram_id=tg_id).info(
            "Getting profile for user"
        )
        try:
            stmt = select(cls.model).where(cls.model.telegram_id == tg_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if not user:
                logger.bind(model=cls.model, telegram_id=tg_id).warning(
                    "User not found for profile"
                )
                return None

            # Check and reset period if needed
            await cls.check_and_reset_period(user, session)
            await session.flush()

            plan = user.plan
            has_paid_plan = plan.name != PlanType.TEST

            # Calculate remaining
            if plan.monthly_analyses is None:
                remaining = -1  # Unlimited
            else:
                remaining = plan.monthly_analyses - user.analyses_used

            return ProfileModel(
                plan_name=plan.name.value,
                analyses_used=user.analyses_used,
                monthly_analyses=plan.monthly_analyses,
                remaining=remaining,
                max_reels_per_request=plan.max_reels_per_request,
                period_start=user.period_start,
                period_end=user.period_end,
                has_paid_plan=has_paid_plan,
            )
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, telegram_id=tg_id
            ).exception("Failed to get profile")
            raise

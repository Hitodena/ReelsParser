from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.custom_enums import PlanType
from app.models import PlanModel

from ..models import Plan
from .base_dao import BaseDAO


class PlanDAO(BaseDAO[Plan]):
    model = Plan

    @classmethod
    async def get_by_active_type(
        cls, plan_type: PlanType, session: AsyncSession, active: bool = True
    ) -> PlanModel | None:
        """
        Retrieves an active plan by its type.

        Args:
            plan_type (PlanType): The type of the plan to retrieve.
            session (AsyncSession): The database session to use for the query.

        Returns:
            PlanModel | None: The matching plan if found, otherwise None.
        """
        logger.bind(model=cls.model, plan_type=plan_type, active=active).info(
            "Getting plan by type"
        )
        stmt = select(cls.model).where(
            cls.model.name == plan_type, cls.model.is_active == active
        )
        try:
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            if not plan:
                logger.bind(
                    model=cls.model, plan_type=plan_type, ctive=active
                ).warning("No active plan found by type")
                return None
            logger.bind(
                model=cls.model, plan_type=plan_type, ctive=active
            ).info("Found plan by type")
            return PlanModel.model_validate(plan)
        except Exception as exc:
            logger.bind(
                error_message=exc,
                model=cls.model,
                plan_type=plan_type,
                ctive=active,
            ).exception("Failed to get plan by type")
            raise

    @classmethod
    async def get_all_active(
        cls, session: AsyncSession, active: bool = True
    ) -> list[PlanModel]:
        """
        Retrieves all active plans.

        Args:
            session (AsyncSession): The database session to use for the query.
            active (bool): Filter by active status. Defaults to True.

        Returns:
            list[PlanModel]: List of active plans.
        """
        logger.bind(model=cls.model, active=active).info(
            "Getting all active plans"
        )
        stmt = select(cls.model).where(cls.model.is_active == active)
        try:
            result = await session.execute(stmt)
            plans = result.scalars().all()
            logger.bind(model=cls.model, active=active, count=len(plans)).info(
                "Found active plans"
            )
            return [PlanModel.model_validate(plan) for plan in plans]
        except Exception as exc:
            logger.bind(
                error_message=exc,
                model=cls.model,
                active=active,
            ).exception("Failed to get all active plans")
            raise

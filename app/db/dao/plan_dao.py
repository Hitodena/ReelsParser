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
    async def get_by_type(
        cls, plan_type: PlanType, session: AsyncSession
    ) -> PlanModel | None:
        """
        Retrieves an active plan by its type.

        Args:
            plan_type (PlanType): The type of the plan to retrieve.
            session (AsyncSession): The database session to use for the query.

        Returns:
            PlanModel | None: The matching plan if found, otherwise None.
        """
        logger.bind(model=cls.model, plan_type=plan_type).info(
            "Getting plan by type"
        )
        stmt = select(cls.model).where(
            cls.model.name == plan_type, cls.model.is_active
        )
        try:
            result = await session.execute(stmt)
            plan = result.scalar_one_or_none()
            if not plan:
                logger.bind(model=cls.model, plan_type=plan_type).warning(
                    "No active plan found by type"
                )
                return None
            logger.bind(model=cls.model, plan_type=plan_type).info(
                "Found plan by type"
            )
            return PlanModel.model_validate(plan)
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, plan_type=plan_type
            ).exception("Failed to get plan by type")
            raise

    @classmethod
    async def get_all_active(cls, session: AsyncSession) -> list[PlanModel]:
        """
        Retrieves all active plans.

        Args:
            session (AsyncSession): The database session to use for the query.

        Returns:
            list[PlanModel]: A list of all active plans.
        """
        logger.bind(model=cls.model).info("Getting all active plans")
        stmt = select(cls.model).where(cls.model.is_active)
        try:
            result = await session.execute(stmt)
            plans = result.scalars().all()
            if not plans:
                logger.bind(model=cls.model).warning("No active plans found")
                return []
            logger.bind(model=cls.model, count=len(plans)).info(
                "Found active plans"
            )
            return [PlanModel.model_validate(plan) for plan in plans]
        except Exception as exc:
            logger.bind(error_message=exc, model=cls.model).exception(
                "Failed to get all active plans"
            )
            raise

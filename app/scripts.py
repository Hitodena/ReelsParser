import asyncio

from loguru import logger
from pydantic import ValidationError

from app.core import load
from app.custom_enums import PlanType
from app.db.dao import PlanDAO
from app.services import DatabaseSessionManager


async def seed():
    config = load()
    db_manager = DatabaseSessionManager(config.environment.get_db_url())
    db_manager.init()

    async def create_plans():
        plans = [
            {
                "name": PlanType.TEST,
                "price": 0,
                "monthly_analyses": 2,
                "max_reels_per_request": 50,
                "is_active": True,
            },
            {
                "name": PlanType.BASE,
                "price": 99000,
                "monthly_analyses": 20,
                "max_reels_per_request": 300,
                "is_active": True,
            },
            {
                "name": PlanType.UNLIMITED,
                "price": 299000,
                "monthly_analyses": None,
                "max_reels_per_request": 1000,
                "is_active": True,
            },
        ]

        plans_created = []

        async with db_manager.session() as session:
            try:
                for plan in plans:
                    plan_db = await PlanDAO.add(session, **plan)
                    plans_created.append(plan_db)
            except Exception:
                pass

        return plans_created

    async with db_manager.session() as session:
        try:
            existing_plans = await PlanDAO.get_all_active(session)
            if not existing_plans:
                plans_count = await create_plans()

                if not plans_count:
                    logger.bind(plans_created_count=len(plans_count)).error(
                        "Failed to create plans"
                    )

                logger.bind(plans_created_count=len(plans_count)).info(
                    "Plans created successfully"
                )

        except ValidationError as exc:
            logger.bind(error_message=exc).info(
                "Failed to get models"
            )
            raise


if __name__ == "__main__":
    asyncio.run(seed())

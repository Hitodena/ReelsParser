from datetime import datetime

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import InstagramAccount
from .base_dao import BaseDAO


class InstagramDAO(BaseDAO):
    model = InstagramAccount

    @classmethod
    async def get_by_login(
        cls, session: AsyncSession, login: str
    ) -> InstagramAccount | None:
        logger.bind(model=cls.model, login=login).info(
            "Getting instagram account by login"
        )
        stmt = (
            select(cls.model)
            .where(cls.model.login == login, cls.model.valid)
            .order_by(cls.model.last_used_at.asc().nullsfirst())
        )
        try:
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()
            if not account:
                logger.bind(model=cls.model, login=login).warning(
                    "No account found by login"
                )
                return None
            logger.bind(model=cls.model, login=login).info(
                "Found instagram account by login"
            )
            return account
        except Exception as exc:
            logger.bind(error_message=exc, model=cls.model, login=login)
            raise

    @classmethod
    async def update_by_login(
        cls,
        session: AsyncSession,
        login: str,
        password: str | None = None,
        last_updated_at: datetime | None = None,
        cookies: dict | None = None,
        valid: bool | None = None,
    ) -> InstagramAccount | None:
        logger.bind(model=cls.model, login=login).info(
            "Updating instagram account by login"
        )
        update_data = {}
        if password:
            update_data["password"] = password
        if last_updated_at:
            update_data["last_updated_at"] = last_updated_at
        if cookies:
            update_data["cookies"] = cookies
        if valid:
            update_data["valid"] = valid
        elif not update_data:
            logger.bind(model=cls.model, login=login).warning(
                "No fields to update"
            )
            return None

        stmt = (
            update(cls.model)
            .where(cls.model.login == login)
            .values(**update_data)
        ).returning(cls.model)

        try:
            result = await session.execute(stmt)
            await session.commit()
            account = result.scalar_one_or_none()
            if not account:
                logger.bind(model=cls.model, login=login).error(
                    "No account updated by login"
                )
                return None
            return account
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, login=login
            ).exception("Failed to update account by login")
            raise

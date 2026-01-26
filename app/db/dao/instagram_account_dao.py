from datetime import datetime

from loguru import logger
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import InstagramAccount
from .base_dao import BaseDAO


class InstagramAccountDAO(BaseDAO):
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
            logger.bind(
                error_message=exc, model=cls.model, login=login
            ).exception("Failed to get account by login")
            raise

    @classmethod
    async def update_by_login(
        cls,
        session: AsyncSession,
        login: str,
        password: str | None = None,
        last_used_at: datetime | None = None,
        cookies: dict | None = None,
        valid: bool | None = None,
    ) -> InstagramAccount | None:
        logger.bind(model=cls.model, login=login).info(
            "Updating instagram account by login"
        )
        update_data = {}
        if password:
            update_data["password"] = password
        if last_used_at:
            update_data["last_used_at"] = last_used_at
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
                logger.bind(model=cls.model, login=login).warning(
                    "No account updated by login"
                )
                return None
            return account
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, login=login
            ).exception("Failed to update account by login")
            raise

    @classmethod
    async def update_validity(
        cls, session: AsyncSession, login: str, valid: bool
    ) -> InstagramAccount | None:
        logger.bind(model=cls.model, login=login, valid=valid).info(
            "Updating validity of instagram account"
        )
        stmt = (
            update(cls.model)
            .where(cls.model.login == login)
            .values(valid=valid)
        ).returning(cls.model)

        try:
            result = await session.execute(stmt)
            await session.commit()
            account = result.scalar_one_or_none()
            if not account:
                logger.bind(model=cls.model, login=login).warning(
                    "No account found to update validity"
                )
                return None
            logger.bind(model=cls.model, login=login).info(
                "Updated validity of instagram account"
            )
            return account
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, login=login
            ).exception("Failed to update validity of account")
            raise

    @classmethod
    async def delete_by_login(
        cls, session: AsyncSession, login: str
    ) -> InstagramAccount | None:
        logger.bind(model=cls.model, login=login).info(
            "Getting instagram account by login"
        )
        stmt = (
            delete(cls.model)
            .where(cls.model.login == login, cls.model.valid)
            .returning(cls.model)
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
                "Deleted instagram account by login"
            )
            return account
        except Exception as exc:
            logger.bind(error_message=exc, model=cls.model, login=login).info(
                "Failed to delete account by login"
            )
            raise

    @classmethod
    async def get_least_used(
        cls, session: AsyncSession
    ) -> InstagramAccount | None:
        logger.bind(model=cls.model).info(
            "Getting least recently used Instagram account"
        )

        stmt = (
            select(cls.model)
            .where(cls.model.valid)
            .order_by(cls.model.last_used_at.asc().nullsfirst())
            .limit(1)
        )

        try:
            result = await session.execute(stmt)
            account = result.scalar_one_or_none()

            if not account:
                logger.bind(model=cls.model).warning("No valid accounts found")
                return None

            logger.bind(
                model=cls.model,
                login=account.login,
                last_used_at=account.last_used_at,
            ).info("Found least recently used account")

            return account

        except Exception as exc:
            logger.bind(error_message=exc, model=cls.model).exception(
                "Failed to get least recently used account"
            )
            raise

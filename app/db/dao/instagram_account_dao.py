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
        """
        Retrieves a valid Instagram account by its login, ordered by last used time.

        Args:
            session (AsyncSession): The database session to use for the query.
            login (str): The login of the Instagram account to retrieve.

        Returns:
            InstagramAccount | None: The matching Instagram account if found, otherwise None.
        """
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
    async def update_validity(
        cls, session: AsyncSession, login: str, valid: bool
    ) -> InstagramAccount | None:
        """
        Updates the validity status of an Instagram account by its login.

        Args:
            session (AsyncSession): The database session to use for the update.
            login (str): The login of the Instagram account to update.
            valid (bool): The new validity status.

        Returns:
            InstagramAccount | None: The updated Instagram account if successful, otherwise None.
        """
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
        """
        Deletes a valid Instagram account by its login.

        Args:
            session (AsyncSession): The database session to use for the deletion.
            login (str): The login of the Instagram account to delete.

        Returns:
            InstagramAccount | None: The deleted Instagram account if successful, otherwise None.
        """
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
            await session.commit()
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
        """
        Retrieves the least recently used valid Instagram account.

        Args:
            session (AsyncSession): The database session to use for the query.

        Returns:
            InstagramAccount | None: The least recently used valid account if found, otherwise None.
        """
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

    @classmethod
    async def update_by_login(
        cls,
        session: AsyncSession,
        login: str,
        cookies: dict | None = None,
        last_used_at: object | None = None,
        valid: bool | None = None,
    ) -> InstagramAccount | None:
        """
        Updates an Instagram account by its login.

        Args:
            session (AsyncSession): The database session to use for the update.
            login (str): The login of the Instagram account to update.
            cookies (dict | None): New cookies to set.
            last_used_at (object | None): New last_used_at timestamp.
            valid (bool | None): New validity status.

        Returns:
            InstagramAccount | None: The updated Instagram account if successful, otherwise None.
        """
        logger.bind(
            model=cls.model,
            login=login,
            cookies=cookies is not None,
            last_used_at=last_used_at,
            valid=valid,
        ).info("Updating instagram account by login")

        values = {}
        if cookies is not None:
            values["cookies"] = cookies
        if last_used_at is not None:
            values["last_used_at"] = last_used_at
        if valid is not None:
            values["valid"] = valid

        if not values:
            logger.bind(model=cls.model, login=login).warning(
                "No values to update"
            )
            return None

        stmt = (
            update(cls.model).where(cls.model.login == login).values(**values)
        ).returning(cls.model)

        try:
            result = await session.execute(stmt)
            await session.commit()
            account = result.scalar_one_or_none()
            if not account:
                logger.bind(model=cls.model, login=login).warning(
                    "No account found to update"
                )
                return None
            logger.bind(model=cls.model, login=login).info(
                "Updated instagram account by login"
            )
            return account
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, login=login
            ).exception("Failed to update account by login")
            raise

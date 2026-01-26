from typing import Any, Generic, Type, TypeVar

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.base import Base

T = TypeVar("T", bound=Base)


class BaseDAO(Generic[T]):
    model: Type[T]

    @classmethod
    async def add(cls, session: AsyncSession, **values: Any) -> T:
        logger.bind(model=cls.model, values=values).info("Adding instance")
        new_instance = cls.model(**values)
        try:
            session.add(new_instance)
            await session.commit()
            await session.refresh(new_instance)
            logger.bind(
                instance=new_instance,
                model=cls.model,
            ).info("Instance added successfully")
            return new_instance
        except Exception as exc:
            logger.bind(
                error_message=exc,
                instance=new_instance,
                model=cls.model,
            ).exception("Failed to add instance")
            await session.rollback()
            raise

    @classmethod
    async def get(cls, session: AsyncSession, pk: Any) -> T | None:
        logger.bind(pk=pk, model=cls.model).info("Getting instance by pk")
        try:
            instance = await session.get(cls.model, pk)
            if not instance:
                logger.bind(pk=pk, model=cls.model).warning(
                    "Instance not found by pk"
                )
                return None
            logger.bind(pk=pk, model=cls.model).info(
                "Instance found successfully by pk"
            )
            return instance
        except Exception as exc:
            logger.bind(error=exc, pk=pk, model=cls.model).exception(
                "Failed to get instance by pk"
            )
            raise

    @classmethod
    async def delete(cls, session: AsyncSession, pk: Any) -> T | None:
        logger.bind(pk=pk, model=cls.model).info("Deleting instance by pk")
        try:
            instance = await session.get(cls.model, pk)
            if not instance:
                logger.bind(pk=pk, model=cls.model).warning(
                    "Instance not found by pk"
                )
                return None
            await session.delete(instance)
            await session.commit()
            logger.bind(pk=pk, model=cls.model).info(
                "Instance deleted successfully by pk"
            )
            return instance
        except Exception as exc:
            logger.bind(error=exc, pk=pk, model=cls.model).exception(
                "Failed to delete instance by pk"
            )
            await session.rollback()
            raise

    @classmethod
    async def get_all(cls, session: AsyncSession, **kwargs) -> list[T] | None:
        logger.bind(model=cls.model, kwargs=kwargs).info(
            "Getting all instances"
        )
        stmt = select(cls.model).filter_by(**kwargs)
        try:
            result = await session.execute(stmt)
            instances = result.scalars().all()
            if not instances:
                logger.bind(kwargs=kwargs, model=cls.model).warning(
                    "No instances found"
                )
                return None
            logger.bind(
                kwargs=kwargs, model=cls.model, instances_count=len(instances)
            ).info("Instances found successfully")
            return list(instances)
        except Exception as exc:
            logger.bind(
                error_message=exc, kwargs=kwargs, model=cls.model
            ).exception("Failed to get all instances")
            raise

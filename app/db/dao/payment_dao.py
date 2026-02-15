from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PaymentModel

from ..models import Payment
from .base_dao import BaseDAO


class PaymentDAO(BaseDAO[Payment]):
    model = Payment

    @classmethod
    async def get_by_invoice(
        cls, invoice_id: str, session: AsyncSession
    ) -> PaymentModel | None:
        """
        Retrieves a payment by its invoice ID.

        Args:
            invoice_id (str): The invoice ID of the payment to retrieve.
            session (AsyncSession): The database session to use for the query.

        Returns:
            PaymentModel | None: The matching payment if found, otherwise None.
        """
        logger.bind(model=cls.model, invoice_id=invoice_id).info(
            "Getting payment by invoice id"
        )
        stmt = select(cls.model).where(cls.model.invoice_id == invoice_id)
        try:
            result = await session.execute(stmt)
            payment = result.scalar_one_or_none()
            if not payment:
                logger.bind(model=cls.model, invoice_id=invoice_id).warning(
                    "No payment found by invoice id"
                )
                return None
            logger.bind(model=cls.model, invoice_id=invoice_id).info(
                "Found payment by invoice id"
            )
            return PaymentModel.model_validate(payment)
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, invoice_id=invoice_id
            ).exception("Failed to get payment by invoice id")
            raise

    @classmethod
    async def mark_paid(
        cls, invoice_id: str, session: AsyncSession
    ) -> PaymentModel | None:
        """
        Marks a payment as paid by its invoice ID.

        Args:
            invoice_id (str): The invoice ID of the payment to mark as paid.
            session (AsyncSession): The database session to use for the update.

        Returns:
            PaymentModel | None: The updated payment if successful, otherwise None.
        """
        logger.bind(model=cls.model, invoice_id=invoice_id).info(
            "Marking payment as paid"
        )
        try:
            stmt = select(cls.model).where(cls.model.invoice_id == invoice_id)
            result = await session.execute(stmt)
            payment = result.scalar_one_or_none()
            if payment:
                payment.status = "paid"
                await session.flush()
                await session.refresh(payment)
                logger.bind(model=cls.model, invoice_id=invoice_id).info(
                    "Payment marked as paid"
                )
                return PaymentModel.model_validate(payment)
            logger.bind(model=cls.model, invoice_id=invoice_id).warning(
                "No payment found to mark as paid"
            )
            return None
        except Exception as exc:
            logger.bind(
                error_message=exc, model=cls.model, invoice_id=invoice_id
            ).exception("Failed to mark payment as paid")
            raise

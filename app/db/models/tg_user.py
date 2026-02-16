from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .payment import Payment
    from .plan import Plan


class TGUser(IDMixin, TimestampMixin, Base):
    __tablename__ = "tg_users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)

    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    plan: Mapped["Plan"] = relationship(
        "Plan", back_populates="tg_users", lazy="joined"
    )

    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="tg_user"
    )

    analyses_used: Mapped[int] = mapped_column(default=0)
    period_start: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    period_end: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def __repr__(self) -> str:
        return f"TGUser(id={self.id}, tg_user)id={self.telegram_id})"

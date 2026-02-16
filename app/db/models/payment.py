from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .plan import Plan
    from .tg_user import TGUser


class Payment(IDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    tg_user_id: Mapped[int] = mapped_column(ForeignKey("tg_users.id"))
    tg_user: Mapped["TGUser"] = relationship(
        "TGUser", back_populates="payments", lazy="joined"
    )

    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    plan: Mapped["Plan"] = relationship("Plan", lazy="joined")

    invoice_id: Mapped[str] = mapped_column(unique=True)
    amount: Mapped[int]
    status: Mapped[str]

    def __repr__(self) -> str:
        return f"Payment(id={self.id}, tg_user_id={self.tg_user_id}, amount={self.amount})"

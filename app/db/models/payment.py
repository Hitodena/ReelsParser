from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin
from .tg_user import TGUser


class Payment(IDMixin, TimestampMixin, Base):
    __tablename__ = "payments"

    tg_user_id: Mapped[int] = mapped_column(ForeignKey("tg_users.id"))
    tg_user: Mapped[TGUser] = relationship(
        TGUser, back_populates="users", lazy="joined"
    )

    invoice_id: Mapped[str] = mapped_column(unique=True)
    amount: Mapped[int]
    status: Mapped[str]

    def __repr__(self) -> str:
        return f"Payment(id={self.id}, tg_user_id={self.tg_user_id}, amount={self.amount})"

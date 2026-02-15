from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin
from .plan import Plan


class TGUser(IDMixin, TimestampMixin, Base):
    __tablename__ = "tg_users"

    telegram_id: Mapped[int] = mapped_column(unique=True)

    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id"))
    plan: Mapped[Plan] = relationship(
        Plan, back_populates="users", lazy="joined"
    )

    analyses_used: Mapped[int] = mapped_column(default=0)
    period_start: Mapped[datetime]
    period_end: Mapped[datetime]

    def __repr__(self) -> str:
        return f"TGUser(id={self.id}, tg_user)id={self.telegram_id})"

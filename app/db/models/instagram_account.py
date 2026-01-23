from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IDMixin, TimestampMixin


class InstagramAccount(IDMixin, TimestampMixin, Base):
    __tablename__ = "instagram_accounts"

    login: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    last_used_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    cookies: Mapped[dict] = mapped_column(JSONB, nullable=True)

    def __repr__(self) -> str:
        return f"CardVariant(id={self.id}, login={self.login})"

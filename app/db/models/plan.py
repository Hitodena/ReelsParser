from sqlalchemy.dialects.postgresql import ENUM as PgEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.custom_enums import PlanType

from .base import Base, IDMixin, TimestampMixin


class Plan(IDMixin, TimestampMixin, Base):
    __tablename__ = "plans"

    name: Mapped[PlanType] = mapped_column(
        PgEnum(
            PlanType,
            name="plan_type_enum",
            create_type=False,
            values_callable=lambda v: [field.value for field in v],
        ),
        nullable=False,
        default=PlanType.BASE,
    )
    price: Mapped[int]
    monthly_analyses: Mapped[int | None]  # None = Unlimited
    max_reels_per_request: Mapped[int]
    is_active: Mapped[bool] = mapped_column(default=True)

    def __repr__(self) -> str:
        return f"Plan(id={self.id}, name={self.name})"

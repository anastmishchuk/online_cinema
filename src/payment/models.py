from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import DECIMAL, Enum as SqlEnum, ForeignKey, String, func, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import TYPE_CHECKING

from ..config.database import Base

if TYPE_CHECKING:
    from ..users.models import User
    from ..orders.models import Order, OrderItem
    from ..movies.models import PurchasedMovie


class PaymentStatus(str, Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        default=datetime.utcnow,
        server_default=func.now(),
        nullable=False
    )
    status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus),
        default=PaymentStatus.successful,
        nullable=False
    )
    amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)
    external_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="payments"
    )
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="payments"
    )
    items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="payment",
        cascade="all, delete-orphan"
    )
    purchased_movies: Mapped[list["PurchasedMovie"]] = relationship(
        "PurchasedMovie",
        back_populates="payment"
    )

    __table_args__ = (
        UniqueConstraint("order_id", "external_payment_id", name="uix_order_external_payment_id"),
    )

    def __str__(self) -> str:
        return (f"Payment {self.id} - User: {self.user_id}, "
                f"Order: {self.order_id}, Amount: {self.amount}")


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    price_at_payment: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    payment: Mapped["Payment"] = relationship(
        "Payment",
        back_populates="items"
    )
    order_item: Mapped["OrderItem"] = relationship(
        "OrderItem",
        back_populates="payment_item"
    )

    def __str__(self) -> str:
        return (f"PaymentItem {self.id} "
                f"(Payment: {self.payment_id}, "
                f"Price: {self.price_at_payment})")

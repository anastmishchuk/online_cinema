from datetime import datetime
from enum import Enum

from sqlalchemy import DECIMAL, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.config.database import Base


class PaymentStatus(str, Enum):
    successful = "successful"
    canceled = "canceled"
    refunded = "refunded"


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    status: Mapped[PaymentStatus] = mapped_column(
        SqlEnum(PaymentStatus),
        default=PaymentStatus.successful,
        nullable=False
    )
    amount: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    external_payment_id: Mapped[str | None] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="payments")
    order: Mapped["Order"] = relationship("Order", back_populates="payments")
    items: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="payment",
        cascade="all, delete-orphan"
    )


class PaymentItem(Base):
    __tablename__ = "payment_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), nullable=False)
    order_item_id: Mapped[int] = mapped_column(ForeignKey("order_items.id"), nullable=False)
    price_at_payment: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)

    payment: Mapped["Payment"] = relationship("Payment", back_populates="items")
    order_item: Mapped["OrderItem"] = relationship("OrderItem")

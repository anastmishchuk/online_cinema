from datetime import datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import (
    Boolean,
    DateTime,
    DECIMAL,
    ForeignKey,
    Enum as SqlEnum,
    Text
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from typing import TYPE_CHECKING

from ..config.database import Base

if TYPE_CHECKING:
    from ..payment.models import Payment, PaymentItem
    from ..users.models import User
    from ..movies.models import Movie


class OrderStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELED = "canceled"


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=datetime.utcnow
    )
    status: Mapped[OrderStatus] = mapped_column(
        SqlEnum(OrderStatus),
        default=OrderStatus.PENDING,
        nullable=False
    )
    total_amount: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=True)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders"
    )
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    refund_requests: Mapped[list["RefundRequest"]] = relationship(
        "RefundRequest",
        back_populates="order",
        cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment",
        back_populates="order"
    )

    def __str__(self):
        return (f"Order {self.id} - User: {self.user_id}, "
                f"Status: {self.status}, Amount: {self.total_amount}")


class OrderItem(Base):
    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False)
    movie_id: Mapped[int] = mapped_column(ForeignKey("movies.id"), nullable=False)
    price_at_order: Mapped[Decimal] = mapped_column(DECIMAL(10, 2), nullable=False)

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items"
    )
    movie: Mapped["Movie"] = relationship(
        "Movie",
        back_populates="order_items"
    )
    payment_item: Mapped[list["PaymentItem"]] = relationship(
        "PaymentItem",
        back_populates="order_item"
    )

    def __str__(self):
        return (f"OrderItem {self.id} "
                f"(Order: {self.order_id}, Movie: {self.movie_id})")


class RefundStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class RefundRequest(Base):
    __tablename__ = "refund_requests"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id"), nullable=False, unique=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[RefundStatus] = mapped_column(
        SqlEnum(RefundStatus),
        default=RefundStatus.PENDING,
        nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)

    user: Mapped["User"] = relationship(
        "User",
        back_populates="refund_requests"
    )
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="refund_requests"
    )

    def __str__(self):
        return (f"RefundRequest {self.id} "
                f"(Order: {self.order_id}, "
                f"User: {self.user_id}, "
                f"Status: {self.status})")

# app/models.py
# This module defines the SQLAlchemy ORM models for the orders and order items.
# It includes the OrderStatus enum and the Order and OrderItem classes with their relationships.

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Numeric, Integer,
    ForeignKey, DateTime, Enum as SAEnum, text
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum

from app.database import Base


class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), nullable=False, index=True)
    total_price = Column(Numeric(12, 2), nullable=False)
    status = Column(
        SAEnum(
            OrderStatus,
            name="order_status_enum",
            values_callable=lambda enum: [s.value for s in enum],
            validate_strings=True,
        ),
        nullable=False,
        default=OrderStatus.PENDING,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationship: one order → many order_items
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self):
        return f"<Order id={self.order_id} user={self.user_id} status={self.status}>"


class OrderItem(Base):
    __tablename__ = "order_items"

    order_item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, server_default=text("gen_random_uuid()"))
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.order_id", ondelete="CASCADE"), nullable=False, index=True)
    product_id = Column(UUID(as_uuid=True), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(12, 2), nullable=False)

    order = relationship("Order", back_populates="items")

    def __repr__(self):
        return f"<OrderItem order={self.order_id} product={self.product_id} qty={self.quantity}>"

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import OrderStatus


# ─────────────────────────────────────────────
# Cart Item (input for checkout)
# ─────────────────────────────────────────────

class CartItemIn(BaseModel):
    """A single item from the user's cart sent during checkout."""

    product_id: uuid.UUID = Field(..., description="UUID of the product")
    quantity: int = Field(..., gt=0, le=1000, description="Must be between 1 and 1000")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Unit price (must be positive)")

    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than zero")
        return round(v, 2)


# ─────────────────────────────────────────────
# Checkout Request
# ─────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    """Payload to create a new order from cart items."""

    user_id: uuid.UUID = Field(..., description="UUID of the user placing the order")
    items: List[CartItemIn] = Field(..., min_length=1, description="At least one item is required")

    @model_validator(mode="after")
    def no_duplicate_products(self) -> CheckoutRequest:
        product_ids = [item.product_id for item in self.items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate products found in cart. Combine quantities instead.")
        return self


# ─────────────────────────────────────────────
# Order Item Response
# ─────────────────────────────────────────────

class OrderItemOut(BaseModel):
    """Response schema for a single order line item."""

    order_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    price: Decimal

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Order Response
# ─────────────────────────────────────────────

class OrderOut(BaseModel):
    """Full order response including all line items."""

    order_id: uuid.UUID
    user_id: uuid.UUID
    total_price: Decimal
    status: OrderStatus
    created_at: datetime
    items: List[OrderItemOut] = []

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────
# Order Status Update Request
# ─────────────────────────────────────────────

class UpdateOrderStatusRequest(BaseModel):
    """Payload to update an order's lifecycle status."""

    status: OrderStatus = Field(..., description="New status value for the order")


# ─────────────────────────────────────────────
# Order List Response (paginated)
# ─────────────────────────────────────────────

class OrderListResponse(BaseModel):
    """Paginated list of orders."""

    total: int
    page: int
    page_size: int
    orders: List[OrderOut]


# ─────────────────────────────────────────────
# Generic Error Response
# ─────────────────────────────────────────────

class ErrorResponse(BaseModel):
    detail: str

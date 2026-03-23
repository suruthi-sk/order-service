from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from app.models import OrderStatus

# CART ITEM INPUT SCHEMA
# Represents a single item sent from frontend during checkout

class CartItemIn(BaseModel):

    product_id: uuid.UUID = Field(..., description="UUID of the product")
    quantity: int = Field(..., gt=0, le=1000, description="Must be between 1 and 1000")
    price: Decimal = Field(..., gt=0, decimal_places=2, description="Unit price (must be positive)")

    # Custom validation for price
    @field_validator("price")
    @classmethod
    def price_must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Price must be greater than zero")
        return round(v, 2)


# CHECKOUT REQUEST SCHEMA
# Full payload to create an order

class CheckoutRequest(BaseModel):

    user_id: uuid.UUID = Field(..., description="UUID of the user placing the order")
    items: List[CartItemIn] = Field(..., min_length=1, description="At least one item is required")

    @model_validator(mode="after")
    def no_duplicate_products(self) -> "CheckoutRequest":
        product_ids = [item.product_id for item in self.items]

        if len(product_ids) != len(set(product_ids)):
            raise ValueError("Duplicate products found in cart. Combine quantities instead.")

        return self

# ORDER ITEM RESPONSE SCHEMA
# Represents each item in an order (output)

class OrderItemOut(BaseModel):
    order_item_id: uuid.UUID
    product_id: uuid.UUID
    quantity: int
    price: Decimal

    model_config = {"from_attributes": True}

# ORDER RESPONSE SCHEMA
# Full order details returned to client
class OrderOut(BaseModel):
    order_id: uuid.UUID
    user_id: uuid.UUID
    total_price: Decimal
    status: OrderStatus
    created_at: datetime

    # Nested list of order items
    items: List[OrderItemOut] = []

    # Enables ORM → schema conversion
    model_config = {"from_attributes": True}

# UPDATE ORDER STATUS REQUEST
# Payload for updating order lifecycle state

class UpdateOrderStatusRequest(BaseModel):
    status: OrderStatus = Field(..., description="New status value for the order")

# PAGINATED ORDER LIST RESPONSE
# Used for listing orders with pagination
class OrderListResponse(BaseModel):

    total: int       
    page: int         
    page_size: int   
    orders: List[OrderOut] 


# GENERIC ERROR RESPONSE
# Standard error structure
class ErrorResponse(BaseModel):
    detail: str
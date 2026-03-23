# app/service.py
# This module contains the core business logic for the Order & Checkout service.
# It defines functions for creating orders, fetching orders, listing orders with filters, and updating order status.
# Each function interacts with the database via SQLAlchemy sessions and raises domain-specific

import uuid
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.exceptions import (
    EmptyCartError,
    InvalidOrderDataError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
)
from app.models import Order, OrderItem, OrderStatus
from app.schemas import CartItemIn, CheckoutRequest

# ALLOWED STATUS TRANSITIONS
VALID_TRANSITIONS = {
    OrderStatus.PENDING: {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED: {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED: {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED: set(),
    OrderStatus.CANCELLED: set(),
}

# Helper function to compute total price from cart items
def _compute_total(items: List[CartItemIn]) -> Decimal:
    return sum(item.price * item.quantity for item in items)

# 1. CREATE ORDER  (uses stored procedure sp_create_order)

def create_order(db: Session, payload: CheckoutRequest) -> Order:
    #Validate empty cart
    if not payload.items:
        raise EmptyCartError()

    #Validate each item
    for item in payload.items:
        if item.price <= 0:
            raise InvalidOrderDataError(
                f"Product '{item.product_id}' has an invalid price: {item.price}"
            )
        if item.quantity <= 0:
            raise InvalidOrderDataError(
                f"Product '{item.product_id}' has an invalid quantity: {item.quantity}"
            )

    # Compute total price
    total_price = _compute_total(payload.items)

    # Generate new order ID
    new_order_id = uuid.uuid4()

    # Prepare arrays for stored procedure
    product_ids = [str(item.product_id) for item in payload.items]
    quantities  = [item.quantity for item in payload.items]
    prices      = [item.price for item in payload.items]

    try:
        # Step 6: Call stored procedure
        db.execute(
            text("""
                CALL sp_create_order(:order_id, :user_id, :total_price, :product_ids, :quantities, :prices)"""),
            {
                "order_id": str(new_order_id),
                "user_id": str(payload.user_id),
                "total_price": total_price,
                "product_ids": product_ids,
                "quantities": quantities,
                "prices": prices,
            }
        )

        # Step 7: Commit transaction
        db.commit()

        # Fetch created order from DB
        order = db.query(Order).filter(Order.order_id == new_order_id).first()

        if not order:
            raise OrderNotFoundError(new_order_id)

        return order

    except Exception as e:
        # 🔹 Step 9: Rollback on failure
        db.rollback()
        raise InvalidOrderDataError(f"Order creation failed: {str(e)}")

# 2. GET ORDER
# Fetch a specific order and all its line items by `order_id`.

def get_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise OrderNotFoundError(order_id)
    return order

# 3. LIST ORDERS  (order history with optional filters + pagination)
# Returns a paginated list of orders, optionally filtered by `user_id` and/or `status`.
# Results are sorted newest-first.

def list_orders(db: Session, user_id: Optional[uuid.UUID] = None, status: Optional[OrderStatus] = None, page: int = 1, page_size: int = 10,) -> dict:

    # Validate pagination parameters
    if page < 1:
        raise InvalidOrderDataError("Page number must be 1 or greater.")
    if page_size < 1 or page_size > 100:
        raise InvalidOrderDataError("Page size must be between 1 and 100.")

    # Build base query
    query = db.query(Order)

    # Apply filters if provided
    if user_id:
        query = query.filter(Order.user_id == user_id)
    if status:
        query = query.filter(Order.status == status)

    # Get total count for pagination metadata
    total  = query.count()

    # Apply sorting and pagination
    orders = (query.order_by(Order.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all())

    # Return paginated response
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "orders": orders,
    }

# 4. UPDATE ORDER STATUS  (uses stored procedure sp_update_order_status)
# Validates the requested status transition before calling the stored procedure to update the order's status.


def update_order_status(db: Session, order_id: uuid.UUID, new_status: OrderStatus) -> Order:

    # Fetch current order to check existing status
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise OrderNotFoundError(order_id)

    # Validate transition in Python before hitting the DB
    allowed = VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise InvalidStatusTransitionError(order.status.value, new_status.value)

    # Call stored procedure (DML: UPDATE orders SET status = ...)
    db.execute(
        text("CALL sp_update_order_status(:order_id, :new_status)"),
        {
            "order_id": str(order_id),
            "new_status": new_status.value,
        }
    )
    db.commit()
    db.refresh(order)

    return order

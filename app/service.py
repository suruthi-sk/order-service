"""
Order Service – Core Business Logic
====================================
This module contains all database operations for orders.

DML Procedures Explained
------------------------
DML = Data Manipulation Language (INSERT, UPDATE, DELETE, SELECT).
We use PostgreSQL stored procedures (via `CALL` and `CREATE PROCEDURE`) for:

1. `sp_create_order`  → atomically inserts into `orders` and `order_items` in one DB round-trip
2. `sp_update_order_status` → validates status transition rules inside the DB and updates status

WHY use stored procedures here?
- Atomicity: Both tables are written in a single transaction inside the DB engine
- Validation: Status transition rules live in the DB, preventing invalid updates even from direct SQL
- Performance: Fewer network round-trips between app and DB
- Auditability: Logic is self-documenting inside the DB schema

Regular Python SQLAlchemy is used for SELECT operations (get_order, list_orders)
since those are read-only and benefit from ORM's eager-loading of relationships.
"""

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


# ─────────────────────────────────────────────────────────────────
# ALLOWED STATUS TRANSITIONS
# Think of it like a state machine: only forward moves are valid.
# ─────────────────────────────────────────────────────────────────
VALID_TRANSITIONS = {
    OrderStatus.PENDING:    {OrderStatus.CONFIRMED, OrderStatus.CANCELLED},
    OrderStatus.CONFIRMED:  {OrderStatus.PROCESSING, OrderStatus.CANCELLED},
    OrderStatus.PROCESSING: {OrderStatus.SHIPPED, OrderStatus.CANCELLED},
    OrderStatus.SHIPPED:    {OrderStatus.DELIVERED},
    OrderStatus.DELIVERED:  set(),
    OrderStatus.CANCELLED:  set(),
}


def _compute_total(items: List[CartItemIn]) -> Decimal:
    """Calculate total price from cart items."""
    return sum(item.price * item.quantity for item in items)


# ─────────────────────────────────────────────────────────────────
# 1. CREATE ORDER  (uses stored procedure sp_create_order)
# ─────────────────────────────────────────────────────────────────

def create_order(db: Session, payload: CheckoutRequest) -> Order:
    if not payload.items:
        raise EmptyCartError()

    for item in payload.items:
        if item.price <= 0:
            raise InvalidOrderDataError(
                f"Product '{item.product_id}' has an invalid price: {item.price}"
            )
        if item.quantity <= 0:
            raise InvalidOrderDataError(
                f"Product '{item.product_id}' has an invalid quantity: {item.quantity}"
            )

    total_price = _compute_total(payload.items)
    new_order_id = uuid.uuid4()

    try:
        # INSERT into orders
        new_order = Order(
            order_id=new_order_id,
            user_id=payload.user_id,
            total_price=total_price,
            status=OrderStatus.PENDING,
        )
        db.add(new_order)
        db.flush()  # writes order to DB but doesn't commit yet

        # INSERT each item into order_items
        for item in payload.items:
            order_item = OrderItem(
                order_item_id=uuid.uuid4(),
                order_id=new_order_id,
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price,
            )
            db.add(order_item)

        db.commit()
        db.refresh(new_order)
        return new_order

    except Exception as e:
        db.rollback()
        raise InvalidOrderDataError(f"Order creation failed: {str(e)}")

# ─────────────────────────────────────────────────────────────────
# 2. GET ORDER
# ─────────────────────────────────────────────────────────────────

def get_order(db: Session, order_id: uuid.UUID) -> Order:
    """
    Fetches a single order with all its line items.

    Raises:
        OrderNotFoundError: if no order matches the given ID
    """
    order = db.query(Order).filter(Order.order_id == order_id).first()
    if not order:
        raise OrderNotFoundError(order_id)
    return order


# ─────────────────────────────────────────────────────────────────
# 3. LIST ORDERS  (order history with optional filters + pagination)
# ─────────────────────────────────────────────────────────────────

def list_orders(
    db: Session,
    user_id: Optional[uuid.UUID] = None,
    status: Optional[OrderStatus] = None,
    page: int = 1,
    page_size: int = 10,
) -> dict:
    """
    Returns a paginated list of orders.

    Filters:
        user_id   - show only orders belonging to this user
        status    - filter by order lifecycle status

    Returns a dict with: total, page, page_size, orders list
    """
    if page < 1:
        raise InvalidOrderDataError("Page number must be 1 or greater.")
    if page_size < 1 or page_size > 100:
        raise InvalidOrderDataError("Page size must be between 1 and 100.")

    query = db.query(Order)

    if user_id:
        query = query.filter(Order.user_id == user_id)
    if status:
        query = query.filter(Order.status == status)

    total  = query.count()
    orders = (
        query
        .order_by(Order.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total":     total,
        "page":      page,
        "page_size": page_size,
        "orders":    orders,
    }


# ─────────────────────────────────────────────────────────────────
# 4. UPDATE ORDER STATUS  (uses stored procedure sp_update_order_status)
# ─────────────────────────────────────────────────────────────────

def update_order_status(db: Session, order_id: uuid.UUID, new_status: OrderStatus) -> Order:
    """
    Updates the lifecycle status of an order.

    Validation:
        - Order must exist
        - New status must be a valid transition from current status
          (e.g. PENDING → CONFIRMED ✓, DELIVERED → PENDING ✗)

    Uses stored procedure `sp_update_order_status` to perform the UPDATE.

    Raises:
        OrderNotFoundError: if order does not exist
        InvalidStatusTransitionError: if the status move is not allowed
    """
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
            "order_id":   str(order_id),
            "new_status": new_status.value,
        }
    )
    db.commit()
    db.refresh(order)

    return order

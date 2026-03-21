"""
Order & Checkout API Routes
============================
All endpoints follow RESTful conventions.
Exception handlers map domain errors → HTTP status codes cleanly.
"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app import service
from app.database import get_db
from app.exceptions import (
    EmptyCartError,
    InvalidOrderDataError,
    InvalidStatusTransitionError,
    OrderNotFoundError,
)
from app.models import OrderStatus
from app.schemas import (
    CheckoutRequest,
    ErrorResponse,
    OrderListResponse,
    OrderOut,
    UpdateOrderStatusRequest,
)

router = APIRouter(prefix="/orders", tags=["Orders"])


# ─────────────────────────────────────────────────────────────────
# POST /orders/checkout  →  create_order()
# ─────────────────────────────────────────────────────────────────

@router.post(
    "/checkout",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Checkout – create a new order from cart items",
    responses={
        400: {"model": ErrorResponse, "description": "Validation or business rule error"},
        422: {"description": "Request body schema error"},
    },
)
def checkout(payload: CheckoutRequest, db: Session = Depends(get_db)):
    """
    **Checkout endpoint** — moves items from the cart into a new order.

    - Validates all items (price > 0, quantity > 0, no duplicates)
    - Computes total price
    - Creates order record + order_items atomically via stored procedure
    - Returns the created order with all line items
    """
    try:
        order = service.create_order(db, payload)
        return order
    except EmptyCartError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except InvalidOrderDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ─────────────────────────────────────────────────────────────────
# GET /orders/{order_id}  →  get_order()
# ─────────────────────────────────────────────────────────────────

@router.get(
    "/{order_id}",
    response_model=OrderOut,
    summary="Get a single order by ID",
    responses={
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def get_order(order_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Fetch a specific order and all its line items by `order_id`.
    """
    try:
        return service.get_order(db, order_id)
    except OrderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ─────────────────────────────────────────────────────────────────
# GET /orders  →  list_orders()
# ─────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=OrderListResponse,
    summary="List orders (order history) with optional filters",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid pagination parameters"},
    },
)
def list_orders(
    user_id:   Optional[uuid.UUID]   = Query(None, description="Filter by user UUID"),
    status:    Optional[OrderStatus] = Query(None, description="Filter by order status"),
    page:      int                   = Query(1,    ge=1,  description="Page number (starts at 1)"),
    page_size: int                   = Query(10,   ge=1, le=100, description="Items per page (max 100)"),
    db: Session = Depends(get_db),
):
    """
    **Order history endpoint** — returns a paginated list of orders.

    - Filter by `user_id` to get a specific user's order history
    - Filter by `status` to show only orders in a lifecycle state
    - Results are sorted newest-first
    """
    try:
        result = service.list_orders(db, user_id=user_id, status=status, page=page, page_size=page_size)
        return result
    except InvalidOrderDataError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ─────────────────────────────────────────────────────────────────
# PATCH /orders/{order_id}/status  →  update_order_status()
# ─────────────────────────────────────────────────────────────────

@router.patch(
    "/{order_id}/status",
    response_model=OrderOut,
    summary="Update the status of an order",
    responses={
        400: {"model": ErrorResponse, "description": "Invalid status transition"},
        404: {"model": ErrorResponse, "description": "Order not found"},
    },
)
def update_order_status(
    order_id: uuid.UUID,
    payload:  UpdateOrderStatusRequest,
    db: Session = Depends(get_db),
):
    """
    **Update order lifecycle status.**

    Valid transitions:
    - `pending` → `confirmed` or `cancelled`
    - `confirmed` → `processing` or `cancelled`
    - `processing` → `shipped` or `cancelled`
    - `shipped` → `delivered`
    - `delivered` → *(terminal, no further updates)*
    - `cancelled` → *(terminal, no further updates)*
    """
    try:
        return service.update_order_status(db, order_id, payload.status)
    except OrderNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidStatusTransitionError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

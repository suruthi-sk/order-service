"""
Tests for Order & Checkout Service
Run with: pytest tests/test_orders.py -v
"""

import uuid
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import Order, OrderItem, OrderStatus
from app.database import get_db


# ── Test Client ───────────────────────────────────────────────────────────────

client = TestClient(app)


# ── Fixtures ──────────────────────────────────────────────────────────────────

def make_order(
    order_id=None,
    user_id=None,
    total_price=Decimal("199.98"),
    status=OrderStatus.PENDING,
):
    order = Order()
    order.order_id    = order_id or uuid.uuid4()
    order.user_id     = user_id or uuid.uuid4()
    order.total_price = total_price
    order.status      = status
    order.created_at  = __import__("datetime").datetime.utcnow()
    order.items       = []
    return order


def make_item(order_id, product_id=None, quantity=2, price=Decimal("99.99")):
    item = OrderItem()
    item.order_item_id = uuid.uuid4()
    item.order_id      = order_id
    item.product_id    = product_id or uuid.uuid4()
    item.quantity      = quantity
    item.price         = price
    return item


# ── Checkout Tests ────────────────────────────────────────────────────────────

class TestCheckout:

    def test_checkout_success(self):
        """Valid checkout request should return 201 with order data."""
        user_id    = str(uuid.uuid4())
        product_id = str(uuid.uuid4())

        mock_order = make_order(user_id=uuid.UUID(user_id))
        mock_item  = make_item(mock_order.order_id, product_id=uuid.UUID(product_id))
        mock_order.items = [mock_item]

        with patch("app.routes.service.create_order", return_value=mock_order):
            response = client.post("/api/v1/orders/checkout", json={
                "user_id": user_id,
                "items": [{"product_id": product_id, "quantity": 2, "price": "99.99"}],
            })

        assert response.status_code == 201
        data = response.json()
        assert data["user_id"] == user_id
        assert len(data["items"]) == 1

    def test_checkout_empty_items(self):
        """Checkout with no items should fail validation at schema level."""
        response = client.post("/api/v1/orders/checkout", json={
            "user_id": str(uuid.uuid4()),
            "items": [],
        })
        assert response.status_code == 422  # Pydantic min_length=1

    def test_checkout_zero_price(self):
        """Item with price=0 should fail Pydantic validation."""
        response = client.post("/api/v1/orders/checkout", json={
            "user_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1, "price": "0"}],
        })
        assert response.status_code == 422

    def test_checkout_negative_quantity(self):
        """Negative quantity should fail Pydantic validation."""
        response = client.post("/api/v1/orders/checkout", json={
            "user_id": str(uuid.uuid4()),
            "items": [{"product_id": str(uuid.uuid4()), "quantity": -1, "price": "10.00"}],
        })
        assert response.status_code == 422

    def test_checkout_duplicate_products(self):
        """Duplicate product_ids in items should be rejected."""
        pid = str(uuid.uuid4())
        response = client.post("/api/v1/orders/checkout", json={
            "user_id": str(uuid.uuid4()),
            "items": [
                {"product_id": pid, "quantity": 1, "price": "10.00"},
                {"product_id": pid, "quantity": 2, "price": "10.00"},
            ],
        })
        assert response.status_code == 422

    def test_checkout_invalid_user_id(self):
        """Non-UUID user_id should be rejected."""
        response = client.post("/api/v1/orders/checkout", json={
            "user_id": "not-a-uuid",
            "items": [{"product_id": str(uuid.uuid4()), "quantity": 1, "price": "10.00"}],
        })
        assert response.status_code == 422


# ── Get Order Tests ───────────────────────────────────────────────────────────

class TestGetOrder:

    def test_get_order_success(self):
        mock_order = make_order()
        with patch("app.routes.service.get_order", return_value=mock_order):
            response = client.get(f"/api/v1/orders/{mock_order.order_id}")
        assert response.status_code == 200
        assert response.json()["order_id"] == str(mock_order.order_id)

    def test_get_order_not_found(self):
        from app.exceptions import OrderNotFoundError
        random_id = uuid.uuid4()
        with patch("app.routes.service.get_order", side_effect=OrderNotFoundError(random_id)):
            response = client.get(f"/api/v1/orders/{random_id}")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_get_order_invalid_uuid(self):
        response = client.get("/api/v1/orders/not-a-uuid")
        assert response.status_code == 422


# ── List Orders Tests ─────────────────────────────────────────────────────────

class TestListOrders:

    def test_list_orders_defaults(self):
        result = {"total": 0, "page": 1, "page_size": 10, "orders": []}
        with patch("app.routes.service.list_orders", return_value=result):
            response = client.get("/api/v1/orders")
        assert response.status_code == 200
        assert response.json()["total"] == 0

    def test_list_orders_filter_by_user(self):
        user_id = str(uuid.uuid4())
        result  = {"total": 1, "page": 1, "page_size": 10, "orders": []}
        with patch("app.routes.service.list_orders", return_value=result) as mock_svc:
            response = client.get(f"/api/v1/orders?user_id={user_id}")
        assert response.status_code == 200

    def test_list_orders_filter_by_status(self):
        result = {"total": 0, "page": 1, "page_size": 10, "orders": []}
        with patch("app.routes.service.list_orders", return_value=result):
            response = client.get("/api/v1/orders?status=pending")
        assert response.status_code == 200

    def test_list_orders_invalid_page(self):
        response = client.get("/api/v1/orders?page=0")
        assert response.status_code == 422

    def test_list_orders_page_size_too_large(self):
        response = client.get("/api/v1/orders?page_size=200")
        assert response.status_code == 422


# ── Update Order Status Tests ─────────────────────────────────────────────────

class TestUpdateOrderStatus:

    def test_update_status_success(self):
        mock_order        = make_order()
        mock_order.status = OrderStatus.CONFIRMED
        order_id = str(mock_order.order_id)
        with patch("app.routes.service.update_order_status", return_value=mock_order):
            response = client.patch(
                f"/api/v1/orders/{order_id}/status",
                json={"status": "confirmed"},
            )
        assert response.status_code == 200
        assert response.json()["status"] == "confirmed"

    def test_update_status_not_found(self):
        from app.exceptions import OrderNotFoundError
        random_id = uuid.uuid4()
        with patch("app.routes.service.update_order_status", side_effect=OrderNotFoundError(random_id)):
            response = client.patch(
                f"/api/v1/orders/{random_id}/status",
                json={"status": "confirmed"},
            )
        assert response.status_code == 404

    def test_update_status_invalid_transition(self):
        from app.exceptions import InvalidStatusTransitionError
        order_id = uuid.uuid4()
        with patch(
            "app.routes.service.update_order_status",
            side_effect=InvalidStatusTransitionError("delivered", "pending"),
        ):
            response = client.patch(
                f"/api/v1/orders/{order_id}/status",
                json={"status": "pending"},
            )
        assert response.status_code == 400

    def test_update_status_invalid_value(self):
        order_id = uuid.uuid4()
        response = client.patch(
            f"/api/v1/orders/{order_id}/status",
            json={"status": "flying"},
        )
        assert response.status_code == 422


# ── Health Check ──────────────────────────────────────────────────────────────

def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

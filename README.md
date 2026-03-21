# Order & Checkout Service

A FastAPI microservice that handles checkout, order creation, and order lifecycle management.

---

## Project Structure

```
order_service/
├── app/
│   ├── __init__.py
│   ├── main.py          ← FastAPI app + startup
│   ├── config.py        ← Environment settings
│   ├── database.py      ← DB engine + session
│   ├── models.py        ← SQLAlchemy ORM models (orders, order_items)
│   ├── schemas.py       ← Pydantic request/response schemas
│   ├── exceptions.py    ← Custom domain exceptions
│   ├── service.py       ← Core business logic (create_order, get_order, ...)
│   └── routes.py        ← FastAPI route handlers
├── sql/
│   └── schema.sql       ← DB tables + stored procedures (run this first!)
├── tests/
│   └── test_orders.py   ← Unit tests
├── requirements.txt
├── .env.example
└── README.md
```

---

## Setup Instructions

### 1. Create & activate virtual environment

```bash
python -m venv venv
source venv/bin/activate        # Linux/Mac
venv\Scripts\activate           # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and set your DATABASE_URL
```

```env
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/order_service_db
```

### 4. Set up the database

Make sure `order_service_db` already exists in PostgreSQL, then run:

```bash
psql -U postgres -d order_service_db -f sql/schema.sql
```

This creates:
- `orders` table
- `order_items` table
- `sp_create_order` stored procedure
- `sp_update_order_status` stored procedure

### 5. Run the service

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit **http://localhost:8000/docs** for the interactive Swagger UI.

---

## API Endpoints

| Method | Endpoint                           | Function                | Description |
|--------|------------------------------------|-------------------------|-------------|
| POST   | `/api/v1/orders/checkout`          | `create_order()`        | Checkout – create order from cart |
| GET    | `/api/v1/orders/{order_id}`        | `get_order()`           | Get a single order |
| GET    | `/api/v1/orders`                   | `list_orders()`         | Order history  |
| PATCH  | `/api/v1/orders/{order_id}/status` | `update_order_status()` | Update order status |
| GET    | `/health`                          | —                       | Health check |

---

## Sample API Calls

### Checkout (create order)

```bash
curl -X POST http://localhost:8000/api/v1/orders/checkout \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22",
    "items": [
      {"product_id": "c2eebc99-9c0b-4ef8-bb6d-6bb9bd380a33", "quantity": 2, "price": "149.99"},
      {"product_id": "d3eebc99-9c0b-4ef8-bb6d-6bb9bd380a44", "quantity": 1, "price": "200.00"}
    ]
  }'
```

### Get order

```bash
curl http://localhost:8000/api/v1/orders/{order_id}
```

### Order history for a user

```bash
curl "http://localhost:8000/api/v1/orders?user_id={user_id}&page=1&page_size=10"
```

### Update order status

```bash
curl -X PATCH http://localhost:8000/api/v1/orders/{order_id}/status \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmed"}'
```

---

## Order Status Lifecycle

```
pending → confirmed → processing → shipped → delivered
   ↓           ↓           ↓
cancelled   cancelled   cancelled
```

Trying to jump states (e.g. `delivered → pending`) returns HTTP 400.

---

## DML Stored Procedures – Why and Where

### Where are they?
- `sql/schema.sql` → procedure definitions
- `app/service.py` → called via `db.execute(text("CALL sp_..."))`

### Why use them?

| Procedure | Why |
|-----------|-----|
| `sp_create_order` | Inserts into **both** `orders` and `order_items` atomically. If your app crashes mid-way, no ghost orders exist. |
| `sp_update_order_status` | Enforces state-machine rules **inside the DB** — so even direct SQL can't make invalid transitions. |

---

## Running Tests

```bash
pytest tests/test_orders.py -v
```

---

## Input Validation Summary

| Rule | Where enforced |
|------|---------------|
| `quantity > 0` | Pydantic schema + DB CHECK |
| `price > 0` | Pydantic schema + DB CHECK + service |
| No duplicate products in cart | Pydantic `model_validator` |
| Valid UUID for user_id, order_id, product_id | Pydantic `uuid.UUID` type |
| Page ≥ 1, page_size 1–100 | FastAPI Query params |
| Valid status transition | Service layer + stored procedure |
| Order exists before update | Service layer + stored procedure |

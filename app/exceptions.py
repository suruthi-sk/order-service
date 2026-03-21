class OrderNotFoundError(Exception):
    """Raised when an order with the given ID does not exist."""
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"Order '{order_id}' not found.")


class InvalidStatusTransitionError(Exception):
    """
    Raised when an invalid status transition is attempted.
    Example: DELIVERED → PENDING is not allowed.
    """
    def __init__(self, current: str, requested: str):
        self.current = current
        self.requested = requested
        super().__init__(
            f"Cannot transition order from '{current}' to '{requested}'."
        )


class EmptyCartError(Exception):
    """Raised when checkout is attempted with no items."""
    def __init__(self):
        super().__init__("Cannot create an order with an empty cart.")


class InvalidOrderDataError(Exception):
    """Raised when order data fails business-rule validation."""
    def __init__(self, message: str):
        super().__init__(message)

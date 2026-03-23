# Raised when an order with the given ID does not exist.
class OrderNotFoundError(Exception):
    def __init__(self, order_id):
        self.order_id = order_id
        super().__init__(f"Order '{order_id}' not found.")


# Raised when an invalid status transition is attempted.
# Example: DELIVERED → PENDING is not allowed.
class InvalidStatusTransitionError(Exception):
    def __init__(self, current: str, requested: str):
        self.current = current
        self.requested = requested
        super().__init__(
            f"Cannot transition order from '{current}' to '{requested}'."
        )


# Raised when checkout is attempted with no items.
class EmptyCartError(Exception):
    def __init__(self):
        super().__init__("Cannot create an order with an empty cart.")


# Raised when order data fails business-rule validation.
class InvalidOrderDataError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
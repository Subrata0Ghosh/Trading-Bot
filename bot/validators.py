import re

def validate_symbol(symbol: str) -> str:
    """
    Validates a trading symbol.
    Must be alphanumeric, uppercase, and between 3 to 15 characters.
    """
    if not symbol:
        raise ValueError("Symbol cannot be empty.")
    
    clean_symbol = symbol.strip().upper()
    
    # Binance symbols are alphanumeric, e.g., BTCUSDT, 1000SHIBUSDT, etc.
    if not re.match(r"^[A-Z0-9]{3,15}$", clean_symbol):
        raise ValueError(
            f"Invalid symbol format '{symbol}'. Symbol must be alphanumeric uppercase (e.g., BTCUSDT)."
        )
    return clean_symbol

def validate_side(side: str) -> str:
    """
    Validates order side. Must be BUY or SELL.
    """
    if not side:
        raise ValueError("Side cannot be empty.")
    
    clean_side = side.strip().upper()
    if clean_side not in ("BUY", "SELL"):
        raise ValueError(f"Invalid side '{side}'. Must be either 'BUY' or 'SELL'.")
    return clean_side

def validate_order_type(order_type: str) -> str:
    """
    Validates order type. Supports MARKET, LIMIT, and STOP_MARKET.
    """
    if not order_type:
        raise ValueError("Order type cannot be empty.")
    
    clean_type = order_type.strip().upper()
    valid_types = ("MARKET", "LIMIT", "STOP_MARKET")
    if clean_type not in valid_types:
        raise ValueError(
            f"Invalid order type '{order_type}'. Supported types: {', '.join(valid_types)}."
        )
    return clean_type

def validate_quantity(quantity) -> float:
    """
    Validates order quantity. Must be a positive number.
    """
    try:
        qty_val = float(quantity)
    except (TypeError, ValueError):
        raise ValueError(f"Quantity must be a valid number, got '{quantity}'.")
    
    if qty_val <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty_val}.")
    return qty_val

def validate_price(price, order_type: str) -> float:
    """
    Validates order price.
    Required and must be a positive number for LIMIT orders.
    For non-LIMIT orders, it returns None or raises an error if price is provided but not needed.
    """
    if order_type == "LIMIT":
        if price is None or str(price).strip() == "":
            raise ValueError("Price is required for LIMIT orders.")
        try:
            price_val = float(price)
        except (TypeError, ValueError):
            raise ValueError(f"Price must be a valid number, got '{price}'.")
        if price_val <= 0:
            raise ValueError(f"Price must be greater than zero, got {price_val}.")
        return price_val
    return None

def validate_stop_price(stop_price, order_type: str) -> float:
    """
    Validates stop price.
    Required and must be a positive number for STOP_MARKET orders.
    """
    if order_type == "STOP_MARKET":
        if stop_price is None or str(stop_price).strip() == "":
            raise ValueError("Stop Price is required for STOP_MARKET orders.")
        try:
            stop_val = float(stop_price)
        except (TypeError, ValueError):
            raise ValueError(f"Stop Price must be a valid number, got '{stop_price}'.")
        if stop_val <= 0:
            raise ValueError(f"Stop Price must be greater than zero, got {stop_val}.")
        return stop_val
    return None

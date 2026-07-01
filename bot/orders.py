import logging
from decimal import Decimal, ROUND_DOWN
from bot.client import BinanceFuturesClient, BinanceAPIException
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price,
)

logger = logging.getLogger(__name__)

def round_to_step(value, step_size) -> float:
    """
    Rounds a float/Decimal value down to the nearest multiple of step_size.
    E.g. round_to_step(0.00532, 0.001) -> 0.005
    """
    if value is None:
        return None
    d_val = Decimal(str(value))
    d_step = Decimal(str(step_size))
    remainder = d_val % d_step
    rounded = d_val - remainder
    return float(rounded.quantize(d_step, rounding=ROUND_DOWN))

def execute_futures_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: float,
    price: float = None,
    stop_price: float = None,
) -> dict:
    """
    Validates the order parameters, prints a request summary,
    and calls the client to place the order on the testnet.
    Returns the parsed and cleaned order response.
    """
    # 1. Validate inputs
    v_symbol = validate_symbol(symbol)
    v_side = validate_side(side)
    v_type = validate_order_type(order_type)
    v_qty = validate_quantity(quantity)
    v_price = validate_price(price, v_type)
    v_stop_price = validate_stop_price(stop_price, v_type)

    # 2. Fetch symbol exchange filters and auto-round to avoid LOT_SIZE / PRICE_FILTER rejections
    try:
        filters = client.get_symbol_filters(v_symbol)
        step_size = filters.get("stepSize")
        tick_size = filters.get("tickSize")
        
        # Round quantity
        rounded_qty = round_to_step(v_qty, step_size)
        if rounded_qty != v_qty:
            logger.info(f"Auto-rounding quantity from {v_qty} to {rounded_qty} to match LOT_SIZE filter ({step_size})")
            v_qty = rounded_qty
            
        # Round price
        if v_price is not None:
            rounded_price = round_to_step(v_price, tick_size)
            if rounded_price != v_price:
                logger.info(f"Auto-rounding price from {v_price} to {rounded_price} to match PRICE_FILTER filter ({tick_size})")
                v_price = rounded_price
                
        # Round stop price
        if v_stop_price is not None:
            rounded_stop = round_to_step(v_stop_price, tick_size)
            if rounded_stop != v_stop_price:
                logger.info(f"Auto-rounding stop price from {v_stop_price} to {rounded_stop} to match PRICE_FILTER filter ({tick_size})")
                v_stop_price = rounded_stop
    except Exception as fe:
        logger.warning(f"Could not apply exchange info precision filters: {fe}. Proceeding with raw values.")

    # 3. Print order request summary
    logger.info("=" * 40)
    logger.info("ORDER REQUEST SUMMARY")
    logger.info("=" * 40)
    logger.info(f"Symbol:     {v_symbol}")
    logger.info(f"Side:       {v_side}")
    logger.info(f"Type:       {v_type}")
    logger.info(f"Quantity:   {v_qty}")
    if v_price is not None:
        logger.info(f"Price:      {v_price}")
    if v_stop_price is not None:
        logger.info(f"Stop Price: {v_stop_price}")
    logger.info("=" * 40)

    # 4. Synchronize time if needed
    if not client.sync_time_done:
        client.sync()

    # 5. Place order
    logger.info("Submitting order to Binance Futures Testnet...")
    try:
        raw_response = client.place_order(
            symbol=v_symbol,
            side=v_side,
            order_type=v_type,
            quantity=v_qty,
            price=v_price,
            stop_price=v_stop_price,
        )
        
        # 6. Extract core details for the user
        order_id = raw_response.get("orderId")
        status = raw_response.get("status")
        executed_qty = raw_response.get("executedQty", "0.0")
        avg_price = raw_response.get("avgPrice")
        
        # Fallback if avgPrice is not available or "0.00000" but cumulative Quote/Qty are present
        if not avg_price or float(avg_price) == 0.0:
            avg_price = raw_response.get("price", "0.0")
            
        logger.info("=" * 40)
        logger.info("SUCCESS: Order Executed Successfully!")
        logger.info("=" * 40)
        logger.info(f"Order ID:     {order_id}")
        logger.info(f"Status:       {status}")
        logger.info(f"Executed Qty: {executed_qty}")
        logger.info(f"Avg Price:    {avg_price}")
        logger.info("=" * 40)

        return {
            "orderId": order_id,
            "status": status,
            "executedQty": executed_qty,
            "avgPrice": avg_price,
            "raw": raw_response
        }

    except BinanceAPIException as api_err:
        logger.error(f"FAILURE: Binance API rejected the order. Detail: {api_err.message}")
        raise
    except ConnectionError as conn_err:
        logger.error(f"FAILURE: Network error occurred. Detail: {conn_err}")
        raise
    except Exception as e:
        logger.error(f"FAILURE: Unexpected error occurred: {e}")
        raise

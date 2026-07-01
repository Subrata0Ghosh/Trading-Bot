import logging
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

    # 2. Print order request summary
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

    # 3. Synchronize time if needed
    if not client.sync_time_done:
        client.sync()

    # 4. Place order
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
        
        # 5. Extract core details for the user
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

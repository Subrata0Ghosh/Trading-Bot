import argparse
import os
import sys
import time
import logging
from dotenv import load_dotenv

from bot.logging_config import setup_logging
from bot.client import BinanceFuturesClient
from bot.orders import execute_futures_order
from bot.validators import (
    validate_symbol,
    validate_side,
    validate_order_type,
    validate_quantity,
    validate_price,
    validate_stop_price
)

# Initialize logger (setup_logging will configure dual destinations)
setup_logging()
logger = logging.getLogger("cli")

# ANSI colors for beautiful terminal output
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
RESET = "\033[0m"
BOLD = "\033[1m"

def load_credentials_or_prompt():
    """
    Loads BINANCE_API_KEY and BINANCE_API_SECRET from environment or .env.
    Prompts the user interactively if they are not set.
    """
    # Load .env file if it exists
    load_dotenv()
    
    api_key = os.getenv("BINANCE_API_KEY")
    api_secret = os.getenv("BINANCE_API_SECRET")
    
    if api_key and api_secret:
        return api_key, api_secret
        
    print(f"\n{YELLOW}{BOLD}[!] API Credentials Not Found{RESET}")
    print("Could not find BINANCE_API_KEY or BINANCE_API_SECRET in environment variables or .env file.")
    
    # Prompt user interactively
    try:
        choice = input(f"Would you like to enter them now? (y/n) [y]: ").strip().lower()
        if choice not in ("", "y", "yes"):
            print(f"{RED}Error: API Credentials are required to proceed.{RESET}")
            sys.exit(1)
            
        print("\nEnter your Binance Futures Testnet API credentials:")
        input_key = input(f"{CYAN}API Key: {RESET}").strip()
        input_secret = input(f"{CYAN}API Secret: {RESET}").strip()
        
        if not input_key or not input_secret:
            print(f"{RED}Error: Key and Secret cannot be blank.{RESET}")
            sys.exit(1)
            
        save_choice = input(f"Would you like to save these credentials to a .env file? (y/n) [y]: ").strip().lower()
        if save_choice not in ("n", "no"):
            with open(".env", "w") as env_file:
                env_file.write(f"BINANCE_API_KEY={input_key}\n")
                env_file.write(f"BINANCE_API_SECRET={input_secret}\n")
            print(f"{GREEN}Success: Credentials saved to .env file!{RESET}")
            
        return input_key, input_secret
    except KeyboardInterrupt:
        print(f"\n{RED}Operation cancelled.{RESET}")
        sys.exit(1)

def track_order_status(client: BinanceFuturesClient, symbol: str, order_id: int):
    """
    Polls the order status in real-time, displays progress, and handles Ctrl+C to cancel the order.
    """
    print(f"\n{YELLOW}{BOLD}[TRACKING] Started tracking order {order_id}...{RESET}")
    print("Press Ctrl+C to stop tracking and choose options to cancel the order.")
    
    try:
        while True:
            # Query status
            status_res = client.get_order_status(symbol, order_id)
            status = status_res.get("status")
            executed_qty = status_res.get("executedQty", "0.0")
            orig_qty = status_res.get("origQty", "0.0")
            
            # Print status line and rewrite it
            sys.stdout.write(f"\r{CYAN}[TRACKING] Status: {status} | Filled: {executed_qty} / {orig_qty} {symbol}{RESET}")
            sys.stdout.flush()
            
            if status in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
                print(f"\n\n{GREEN}{BOLD}[SUCCESS] Order tracking complete. Final Status: {status}{RESET}\n")
                break
                
            time.sleep(2)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}[!] Order tracking stopped by user.{RESET}")
        cancel_choice = input(f"{CYAN}Would you like to cancel this active order on the exchange? (y/n) [y]: {RESET}").strip().lower()
        if cancel_choice not in ("n", "no"):
            print(f"{YELLOW}Cancelling order {order_id} on the exchange...{RESET}")
            try:
                cancel_res = client.cancel_order(symbol, order_id)
                print(f"{GREEN}{BOLD}[SUCCESS] Order {order_id} cancelled! (Status: {cancel_res.get('status')}){RESET}\n")
            except Exception as ce:
                print(f"{RED}Failed to cancel order: {ce}{RESET}\n")
        else:
            print(f"{YELLOW}Order {order_id} left active on exchange.{RESET}\n")

def run_interactive_mode(client: BinanceFuturesClient):
    """
    Runs a guided, interactive terminal CLI menu to place an order.
    """
    print("\n" + "=" * 50)
    print(f"{GREEN}{BOLD}      BINANCE FUTURES TESTNET INTERACTIVE CLI      {RESET}")
    print("=" * 50)
    
    try:
        # 1. Symbol Input
        while True:
            symbol_input = input(f"{CYAN}Enter Symbol (e.g. BTCUSDT) [BTCUSDT]: {RESET}").strip()
            if not symbol_input:
                symbol_input = "BTCUSDT"
            try:
                symbol = validate_symbol(symbol_input)
                break
            except ValueError as e:
                print(f"{RED}Invalid input: {e}{RESET}")

        # 2. Side Input
        while True:
            print(f"\nSelect Side:")
            print("  1. BUY (Long)")
            print("  2. SELL (Short)")
            side_choice = input(f"{CYAN}Enter selection (1 or 2): {RESET}").strip()
            if side_choice == "1":
                side = "BUY"
                break
            elif side_choice == "2":
                side = "SELL"
                break
            else:
                try:
                    side = validate_side(side_choice)
                    break
                except ValueError as e:
                    print(f"{RED}Invalid input: Please select 1 or 2, or enter BUY/SELL.{RESET}")

        # 3. Order Type Input
        while True:
            print(f"\nSelect Order Type:")
            print("  1. MARKET")
            print("  2. LIMIT")
            print("  3. STOP_MARKET")
            type_choice = input(f"{CYAN}Enter selection (1-3): {RESET}").strip()
            if type_choice == "1":
                order_type = "MARKET"
                break
            elif type_choice == "2":
                order_type = "LIMIT"
                break
            elif type_choice == "3":
                order_type = "STOP_MARKET"
                break
            else:
                try:
                    order_type = validate_order_type(type_choice)
                    break
                except ValueError as e:
                    print(f"{RED}Invalid input: Please select 1, 2, or 3, or enter MARKET/LIMIT/STOP_MARKET.{RESET}")

        # 4. Quantity Input
        while True:
            qty_input = input(f"\n{CYAN}Enter Quantity (e.g. 0.001): {RESET}").strip()
            try:
                quantity = validate_quantity(qty_input)
                break
            except ValueError as e:
                print(f"{RED}Invalid input: {e}{RESET}")

        # 5. Price Input (only for LIMIT)
        price = None
        if order_type == "LIMIT":
            while True:
                price_input = input(f"{CYAN}Enter Limit Price: {RESET}").strip()
                try:
                    price = validate_price(price_input, order_type)
                    break
                except ValueError as e:
                    print(f"{RED}Invalid input: {e}{RESET}")

        # 6. Stop Price Input (only for STOP_MARKET)
        stop_price = None
        if order_type == "STOP_MARKET":
            while True:
                stop_input = input(f"{CYAN}Enter Stop Trigger Price: {RESET}").strip()
                try:
                    stop_price = validate_stop_price(stop_input, order_type)
                    break
                except ValueError as e:
                    print(f"{RED}Invalid input: {e}{RESET}")

        # 7. Final Order Confirmation
        print("\n" + "-" * 40)
        print(f"{YELLOW}{BOLD}ORDER DETAILS FOR CONFIRMATION:{RESET}")
        print(f"  Symbol:     {symbol}")
        print(f"  Side:       {side}")
        print(f"  Type:       {order_type}")
        print(f"  Quantity:   {quantity}")
        if price is not None:
            print(f"  Price:      {price}")
        if stop_price is not None:
            print(f"  Stop Price: {stop_price}")
        print("-" * 40)
        
        confirm = input(f"{CYAN}Do you want to submit this order? (yes/no) [yes]: {RESET}").strip().lower()
        if confirm in ("", "y", "yes"):
            try:
                res = execute_futures_order(
                    client=client,
                    symbol=symbol,
                    side=side,
                    order_type=order_type,
                    quantity=quantity,
                    price=price,
                    stop_price=stop_price,
                )
                
                # If order is LIMIT/STOP_MARKET and not filled instantly, prompt to track
                if res and res.get("status") not in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
                    track_choice = input(f"{CYAN}Would you like to track this order's execution status in real-time? (y/n) [y]: {RESET}").strip().lower()
                    if track_choice not in ("n", "no"):
                        track_order_status(client, symbol, res.get("orderId"))
            except Exception as e:
                # The exception detail has already been logged, we show a clean console error
                print(f"\n{RED}{BOLD}[!] Order execution failed: {e}{RESET}\n")
        else:
            print(f"\n{YELLOW}Order submission cancelled by user.{RESET}")

    except KeyboardInterrupt:
        print(f"\n{RED}Interactive session interrupted. Exiting.{RESET}")
        sys.exit(0)

def main():
    parser = argparse.ArgumentParser(
        description="Binance Futures Testnet (USDT-M) Simplified Trading Bot CLI."
    )
    # Define arguments
    parser.add_argument("--symbol", type=str, help="Trading symbol (e.g. BTCUSDT)")
    parser.add_argument("--side", type=str, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument("--type", type=str, choices=["MARKET", "LIMIT", "STOP_MARKET", "market", "limit", "stop_market"], help="Order type")
    parser.add_argument("--qty", "--quantity", type=float, help="Order quantity")
    parser.add_argument("--price", type=float, help="Price (required for LIMIT)")
    parser.add_argument("--stop-price", type=float, help="Trigger price (required for STOP_MARKET)")
    parser.add_argument("--test-connection", action="store_true", help="Pings the server and verifies connectivity")
    parser.add_argument("--interactive", "-i", action="store_true", help="Launch interactive prompts")
    parser.add_argument("--track", "-t", action="store_true", help="Track order status in real-time until filled or cancelled")

    args = parser.parse_args()

    # Load credentials
    api_key, api_secret = load_credentials_or_prompt()
    client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)

    # If test connection requested
    if args.test_connection:
        print(f"{CYAN}Testing connection to Binance Futures Testnet...{RESET}")
        try:
            client.ping()
            print(f"{GREEN}{BOLD}Ping successful! Web server is reachable.{RESET}")
            client.sync()
            print(f"{GREEN}{BOLD}Successfully synced and authenticated with Testnet API!{RESET}")
        except Exception as e:
            print(f"{RED}{BOLD}Connection Test Failed!{RESET}")
            print(f"Details: {e}")
            sys.exit(1)
        sys.exit(0)

    # Determine if we should go to interactive mode
    # If no arguments (or only --interactive) are passed, go to interactive mode
    has_params = any([args.symbol, args.side, args.type, args.qty is not None])
    
    if args.interactive or not has_params:
        try:
            run_interactive_mode(client)
        except Exception as e:
            logger.error(f"Interactive session error: {e}")
            sys.exit(1)
    else:
        # Standard argument-based execution
        try:
            # Let validators handle case conversion and checks
            res = execute_futures_order(
                client=client,
                symbol=args.symbol,
                side=args.side,
                order_type=args.type,
                quantity=args.qty,
                price=args.price,
                stop_price=args.stop_price,
            )
            # Check if tracking flag is active and order is tracking eligible
            if args.track and res and res.get("status") not in ("FILLED", "CANCELED", "REJECTED", "EXPIRED"):
                track_order_status(client, args.symbol.upper().strip(), res.get("orderId"))
        except Exception as e:
            logger.error(f"Error executing command-line order: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main()

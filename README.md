# Binance Futures Testnet Trading Bot

A simplified, robust Python trading bot designed to place Market and Limit orders on the **Binance Futures Testnet (USDT-M)**. It features strict client-side validation, clean dual-destination logging, error handling, and a highly polished interactive CLI mode.

---

## Features

- **Order Types**: Supports `MARKET`, `LIMIT`, and `STOP_MARKET` (Bonus) order types.
- **Dual Side Support**: Seamlessly executes both `BUY` (Long) and `SELL` (Short) trades.
- **Two CLI Modes**:
  - **Direct Arguments**: Fast execution via command-line flags.
  - **Interactive CLI Menu**: A guided, step-by-step user interface with real-time input validation and confirmation prompts.
- **Time Synchronization**: Automatically fetches server time from Binance to align local system clock offset, eliminating `recvWindow` errors.
- **Comprehensive Logging**:
  - **Stdout (Console)**: Clean, color-coded, user-friendly indicators (`[SUCCESS]`, `[ERROR]`, `[INFO]`).
  - **File (`trading_bot.log`)**: Full DEBUG-level traceability containing API URLs, payload parameters, headers, signing details, responses, and network tracebacks.
- **Fail-Safe Validation**: Checks symbols, quantity sizes, sides, and prices before submitting to minimize API overhead and rate-limit penalties.

---

## Setup Instructions

### 1. Prerequisites
Ensure you have Python 3.8+ installed on your system.

### 2. Clone and Install Dependencies
Navigate to the project root and install the required packages:
```bash
pip install -r requirements.txt
```

### 3. Obtain API Credentials
1. Register and sign in to the [Binance Futures Testnet](https://testnet.binancefuture.com).
2. Generate an API Key and Secret Key from the testnet dashboard.

### 4. Configure Environment Variables
Copy `.env.example` to a new file named `.env`:
```bash
copy .env.example .env
```
Open `.env` and fill in your keys:
```env
BINANCE_API_KEY=your_testnet_api_key_here
BINANCE_API_SECRET=your_testnet_api_secret_here
```
*Note: If the application does not find `.env` or system environment keys, it will prompt you interactively to input them and offer to save them automatically.*

---

## How to Run (Examples)

### 1. Test Connectivity
Verify that your API keys are valid and the Binance server is reachable:
```bash
python cli.py --test-connection
```

### 2. Interactive CLI Mode (Recommended)
Simply run the script without any parameters to launch the interactive interface:
```bash
python cli.py
```
This mode will guide you through:
- Choosing/confirming the symbol (default: `BTCUSDT`)
- Selecting order side (`BUY` / `SELL`)
- Selecting order type (`MARKET` / `LIMIT` / `STOP_MARKET`)
- Validating your input quantity and price
- Displaying a summary card and requesting confirmation before placing the trade.

### 3. Direct Command-Line Arguments

#### Place a MARKET Order:
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --qty 0.001
```

#### Place a LIMIT Order:
```bash
python cli.py --symbol BTCUSDT --side BUY --type LIMIT --qty 0.001 --price 60000
```

#### Place a STOP_MARKET Order (Bonus Type):
```bash
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --qty 0.002 --stop-price 59500
```

---

## Assumptions and Design Decisions

1. **Direct REST Integration**: Handled using `requests` to guarantee absolute control over requests/response cycles, logging formats, signing algorithms, and to avoid external dependency drift of full wrapper libraries.
2. **USDT-M Margin Default**: The endpoint uses `https://testnet.binancefuture.com` which aligns with USDS-M contract parameters (`/fapi/v1/order`).
3. **Price Precision & Step Sizes**: Real exchange orders are subject to tick size and lot size limitations (e.g. BTCUSDT requires specific step size decimals). We assume the user inputs values conforming to these limits. (In case of mismatch, the Binance API returns a clear error code which is printed and logged).
4. **Time Sync Offset**: Server and local timestamps are aligned during initialization by fetching `/fapi/v1/time` to prevent clock-drift issues.

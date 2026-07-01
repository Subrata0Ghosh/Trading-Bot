import hashlib
import hmac
import logging
import time
import urllib.parse
import requests

logger = logging.getLogger(__name__)

class BinanceFuturesClient:
    """
    Client for interacting with the Binance Futures Testnet (USDT-M) API.
    """
    def __init__(self, api_key: str, api_secret: str, base_url: str = "https://testnet.binancefuture.com"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        # Set API Key header
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        })
        self.time_offset = 0
        self.sync_time_done = False
        self._exchange_info_cache = None
        # Determine if we are in mock simulation mode
        self.is_mock = (
            self.api_key.lower().strip() == "mock" or 
            self.api_secret.lower().strip() == "mock" or
            not self.api_key or
            not self.api_secret
        )

    def sync_time(self):
        """
        Synchronizes local system time with Binance server time to avoid recvWindow errors.
        """
        if self.is_mock:
            logger.info("Time synced (Simulation Mode). Offset: 0 ms")
            self.sync_time_done = True
            return

        try:
            logger.debug("Syncing time with Binance server...")
            url = f"{self.base_url}/fapi/v1/time"
            start_local = int(time.time() * 1000)
            
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            end_local = int(time.time() * 1000)
            server_time = response.json()["serverTime"]
            
            # Simple latency estimate: round-trip time / 2
            rtt = (end_local - start_local)
            estimated_server_time = server_time - (rtt // 2)
            self.time_offset = estimated_server_time - start_local
            self.sync_time_done = True
            
            logger.info(f"Time synced. Local-to-server offset: {self.time_offset} ms (RTT: {rtt} ms)")
            logger.debug(f"Estimated Server Time: {estimated_server_time}, Local Time: {start_local}")
        except Exception as e:
            logger.warning(f"Failed to sync time with server: {e}. Using local system time.")
            self.time_offset = 0

    def _get_timestamp(self) -> int:
        """
        Returns the synchronized timestamp in milliseconds.
        """
        if not self.sync_time_done:
            self.sync(timeout=5)  # Fallback sync
        local_now = int(time.time() * 1000)
        return local_now + self.time_offset

    def sync(self, timeout=10):
        """
        Explicitly sync time or perform a quick ping to test credentials.
        """
        self.sync_time()

    def _sign(self, query_string: str) -> str:
        """
        Generates HMAC-SHA256 signature for the given query string.
        """
        if self.is_mock:
            return "mocked_signature_hash_value"
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _request(self, method: str, path: str, params: dict = None, signed: bool = False) -> dict:
        """
        Performs an HTTP request to the Binance Futures API.
        Handles query formatting, signing, logging, and error handling.
        """
        url = f"{self.base_url}{path}"
        
        # Prepare parameters copy
        req_params = params.copy() if params else {}
        
        if signed:
            # Inject timestamp
            req_params["timestamp"] = self._get_timestamp()
            # If recvWindow is not set, set a reasonable default
            if "recvWindow" not in req_params:
                req_params["recvWindow"] = 5000
                
            # Convert boolean values to strings that Binance expects ('true'/'false')
            for k, v in list(req_params.items()):
                if isinstance(v, bool):
                    req_params[k] = str(v).lower()
            
            # Binance signature needs parameters sorted or ordered in standard query string
            # URL encode params
            query_string = urllib.parse.urlencode(req_params)
            # Sign the parameters string
            signature = self._sign(query_string)
            # Append signature
            req_params["signature"] = signature

        # Prepare request details for logging (hiding API secrets, masking API key)
        masked_headers = dict(self.session.headers)
        if "X-MBX-APIKEY" in masked_headers and masked_headers["X-MBX-APIKEY"]:
            key = masked_headers["X-MBX-APIKEY"]
            masked_headers["X-MBX-APIKEY"] = f"{key[:6]}...{key[-6:]}" if len(key) > 12 else "***"

        logger.debug(f"API Request: {method} {url}")
        logger.debug(f"Headers: {masked_headers}")
        logger.debug(f"Params (Raw): {req_params}")

        # If in Mock simulation mode, skip requests and return mock data
        if self.is_mock:
            mock_response_body = {}
            mock_status_code = 200
            
            if path == "/fapi/v1/ping":
                mock_response_body = {}
            elif path == "/fapi/v1/time":
                mock_response_body = {"serverTime": int(time.time() * 1000)}
            elif path == "/fapi/v1/exchangeInfo":
                mock_response_body = {
                    "timezone": "UTC",
                    "serverTime": int(time.time() * 1000),
                    "symbols": []
                }
            elif path == "/fapi/v1/order":
                if method.upper() == "POST":
                    order_type = req_params.get("type", "MARKET")
                    qty = req_params.get("quantity", "0.0")
                    price = req_params.get("price", "0.0")
                    stop_price = req_params.get("stopPrice", "0.0")
                    
                    mock_response_body = {
                        "clientOrderId": f"mock_order_{int(time.time())}",
                        "cumQty": qty if order_type == "MARKET" else "0.0",
                        "cumQuote": "0.0",
                        "executedQty": qty if order_type == "MARKET" else "0.0",
                        "orderId": 12831923812 + (int(time.time()) % 100000),
                        "avgPrice": price if order_type == "LIMIT" else (stop_price if order_type == "STOP_MARKET" else "58250.50"),
                        "origQty": qty,
                        "price": price,
                        "reduceOnly": False,
                        "side": req_params.get("side", "BUY"),
                        "positionSide": "BOTH",
                        "status": "FILLED" if order_type == "MARKET" else "NEW",
                        "stopPrice": stop_price,
                        "closePosition": False,
                        "symbol": req_params.get("symbol", "BTCUSDT"),
                        "timeInForce": req_params.get("timeInForce", "GTC"),
                        "type": order_type,
                        "origType": order_type,
                        "updateTime": int(time.time() * 1000)
                    }
                elif method.upper() == "DELETE":
                    mock_response_body = {
                        "orderId": int(req_params.get("orderId", 12831923812)),
                        "symbol": req_params.get("symbol", "BTCUSDT"),
                        "status": "CANCELED"
                    }
                elif method.upper() == "GET":
                    # Simulate dynamic filling: fills after ~5 seconds depending on seconds modulo
                    is_filled = (int(time.time()) % 10) > 4
                    qty = "0.005"
                    mock_response_body = {
                        "orderId": int(req_params.get("orderId", 12831923812)),
                        "symbol": req_params.get("symbol", "BTCUSDT"),
                        "status": "FILLED" if is_filled else "NEW",
                        "price": "59000.0",
                        "origQty": qty,
                        "executedQty": qty if is_filled else "0.0",
                        "type": "LIMIT",
                        "side": "BUY",
                        "updateTime": int(time.time() * 1000)
                    }
            
            logger.debug(f"API Response Code: {mock_status_code} (Simulated)")
            logger.debug(f"API Response Body: {mock_response_body} (Simulated)")
            return mock_response_body

        # Send request
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=req_params, timeout=15)
            elif method.upper() == "POST":
                # Binance signed POST endpoints accept parameters in the body (form-encoded)
                response = self.session.post(url, data=req_params, timeout=15)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=req_params, timeout=15)
            else:
                raise ValueError(f"Unsupported request method: {method}")

            # Log response
            logger.debug(f"API Response Code: {response.status_code}")
            logger.debug(f"API Response Body: {response.text}")

            # Handle non-200 responses
            if not response.ok:
                try:
                    error_data = response.json()
                    error_msg = error_data.get("msg", "Unknown error")
                    error_code = error_data.get("code", "Unknown code")
                    raise BinanceAPIException(error_msg, error_code, response.status_code)
                except ValueError:
                    # Not JSON
                    raise BinanceAPIException(response.text, -1, response.status_code)
            
            return response.json()

        except requests.exceptions.RequestException as req_err:
            logger.error(f"Network error during request {method} {path}: {req_err}")
            raise ConnectionError(f"Network error contacting Binance API: {req_err}")

    def ping(self) -> dict:
        """
        Test connectivity to the Futures REST API.
        """
        return self._request("GET", "/fapi/v1/ping")

    def get_server_time(self) -> dict:
        """
        Retrieve current server time.
        """
        return self._request("GET", "/fapi/v1/time")

    def get_exchange_info(self) -> dict:
        """
        Current exchange trading rules and symbol information.
        """
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_symbol_filters(self, symbol: str) -> dict:
        """
        Retrieves precision, tick size, step size, and min notional rules for a symbol.
        Uses caching to avoid fetching huge exchangeInfo payloads multiple times.
        """
        symbol = symbol.upper().strip()

        if self.is_mock:
            return {
                "pricePrecision": 2,
                "quantityPrecision": 3,
                "tickSize": "0.01",
                "stepSize": "0.001",
                "minNotional": "5.0"
            }

        # Fetch and cache exchangeInfo if not already done
        if not self._exchange_info_cache:
            logger.debug("Fetching exchange information from Binance...")
            self._exchange_info_cache = self.get_exchange_info()

        # Find symbol rules
        symbol_info = None
        for s in self._exchange_info_cache.get("symbols", []):
            if s.get("symbol") == symbol:
                symbol_info = s
                break

        if not symbol_info:
            raise ValueError(f"Symbol '{symbol}' not found in Binance exchange rules.")

        # Default filters fallback
        filters = {
            "pricePrecision": symbol_info.get("pricePrecision", 2),
            "quantityPrecision": symbol_info.get("quantityPrecision", 3),
            "tickSize": "0.01",
            "stepSize": "0.001",
            "minNotional": "5.0"
        }

        # Parse filters list
        for f in symbol_info.get("filters", []):
            f_type = f.get("filterType")
            if f_type == "PRICE_FILTER":
                filters["tickSize"] = f.get("tickSize", "0.01")
            elif f_type == "LOT_SIZE":
                filters["stepSize"] = f.get("stepSize", "0.001")
            elif f_type == "MIN_NOTIONAL":
                filters["minNotional"] = f.get("notional", "5.0")

        return filters

    def place_order(self, symbol: str, side: str, order_type: str, quantity: float, price: float = None, stop_price: float = None) -> dict:
        """
        Places a futures order.
        """
        params = {
            "symbol": symbol,
            "side": side,
            "type": order_type,
            "quantity": str(quantity),
        }

        if order_type == "LIMIT":
            params["price"] = str(price)
            # Default to GTC (Good Till Cancelled) for LIMIT orders
            params["timeInForce"] = "GTC"
        elif order_type == "STOP_MARKET":
            params["stopPrice"] = str(stop_price)

        return self._request("POST", "/fapi/v1/order", params=params, signed=True)

    def get_order_status(self, symbol: str, order_id: int) -> dict:
        """
        Query standard order details.
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        return self._request("GET", "/fapi/v1/order", params=params, signed=True)

    def cancel_order(self, symbol: str, order_id: int) -> dict:
        """
        Cancel an active order.
        """
        params = {
            "symbol": symbol,
            "orderId": order_id
        }
        return self._request("DELETE", "/fapi/v1/order", params=params, signed=True)


class BinanceAPIException(Exception):
    """
    Exception raised when the Binance API returns an error response.
    """
    def __init__(self, message: str, code: int, status_code: int):
        super().__init__(f"Binance API Error {code}: {message} (HTTP {status_code})")
        self.message = message
        self.code = code
        self.status_code = status_code

import requests
import json
import datetime
import pytz
from dhanhq import dhanhq

class DhanHandler:
    def __init__(self, client_id, access_token):
        """
        Initializes the Dhan API client.
        """
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co/v2"
        
        # Headers for raw API calls (needed for Super Orders)
        self.headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # We use the library for standard calls, but raw requests for specific complex ones
            self.dhan = dhanhq(client_id, access_token)
            print("[DhanHandler]: Dhan client initialized successfully.")
        except Exception as e:
            print(f"[DhanHandler]: FATAL ERROR - Could not initialize Dhan client: {e}")
            raise

    # --- MARKET HOURS & AMO LOGIC ---
    def is_market_open(self) -> bool:
        """
        Checks if the Indian market (NSE/BSE) is open.
        Returns False on Weekends or before 9:15 AM / after 3:30 PM.
        """
        try:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(tz)
            
            # Weekend Check (Sat=5, Sun=6)
            if now.weekday() >= 5: 
                return False
            
            # Time Check (9:15 AM - 3:30 PM)
            market_open = now.replace(hour=9, minute=15, second=0)
            market_close = now.replace(hour=15, minute=30, second=0)
            
            return market_open <= now <= market_close
        except:
            return False

    # --- PHASE 1: FUNDS ---
    def get_funds(self):
        """Fetches available trading balance."""
        try:
            url = f"{self.base_url}/fundlimit"
            response = requests.get(url, headers=self.headers)
            data = response.json()
            
            # Handle potential API typo "availabelBalance" vs "availableBalance"
            balance = data.get("availabelBalance", data.get("availableBalance", 0.0))
            return float(balance)
        except Exception as e:
            print(f"[DhanHandler]: Error fetching funds: {e}")
            return None

    # --- PHASE 2: PORTFOLIO ---
    def get_holdings_summary(self):
        """Fetches long-term holdings summary."""
        try:
            url = f"{self.base_url}/holdings"
            response = requests.get(url, headers=self.headers)
            data = response.json()
            
            holdings = data.get("data") if isinstance(data, dict) else data

            if not holdings or len(holdings) == 0:
                return "You have no long-term holdings."
                
            summary = []
            for item in holdings[:5]: # Limit to top 5
                symbol = item.get("tradingSymbol")
                qty = item.get("totalQty")
                summary.append(f"{qty} shares of {symbol}")
            
            text = ", ".join(summary)
            return f"You are holding: {text}."
        except Exception as e:
            print(f"[DhanHandler]: Error fetching holdings: {e}")
            return "I couldn't fetch your holdings."
        
    def get_positions_summary(self):
        """Fetches intraday open positions."""
        try:
            url = f"{self.base_url}/positions"
            response = requests.get(url, headers=self.headers)
            positions = response.json()
            
            total_pl = 0.0
            open_positions = []
            
            for pos in positions:
                pl = pos.get("unrealizedProfit", 0.0)
                total_pl += pl
                if pos.get("netQty", 0) != 0:
                    open_positions.append(f"{pos['tradingSymbol']} ({pl:.2f})")
            
            status = "profit" if total_pl >= 0 else "loss"
            pos_text = ", ".join(open_positions) if open_positions else "no open positions"
            
            return f"Total intraday P&L is a {status} of {abs(total_pl):.2f} rupees. Active: {pos_text}."
        except Exception as e:
            print(f"[DhanHandler]: Error fetching positions: {e}")
            return "I couldn't fetch your positions."

    # --- PHASE 3: LIVE MARKET DATA ---
    def get_live_price(self, security_id, exchange_segment="NSE_EQ"):
        """Fetches LTP (Last Traded Price)."""
        try:
            url = f"{self.base_url}/marketfeed/ltp"
            payload = { exchange_segment: [int(security_id)] }
            
            response = requests.post(url, headers=self.headers, json=payload)
            data = response.json()
            
            if data.get("status") == "success":
                market_data = data.get("data", {}).get(exchange_segment, {})
                instrument_data = market_data.get(str(security_id))
                if instrument_data:
                    return instrument_data.get("last_price")
            return None
        except Exception as e:
            print(f"[DhanHandler]: Error fetching price: {e}")
            return None

    # --- MAIN ORDER ROUTER ---
    def place_voice_order(self, order_details: dict) -> str:
        """
        Central function to handle Limit, Market, and Super Orders.
        """
        try:
            # 1. Validation
            if not order_details.get("action"): return "I don't know if you want to Buy or Sell."
            if not order_details.get("quantity"): return "Quantity is missing."
            if not order_details.get("security_id"): return "Security ID is missing."

            # 2. Check funds before proceeding (Buying only)
            if order_details["action"].upper() == "BUY":
                funds = self.get_funds()
                if funds is not None:
                    # Determine estimated price
                    if order_details.get("order_type") == "LIMIT":
                        price = float(order_details.get("price", 0.0))
                    else:
                        price = float(self.get_live_price(order_details["security_id"]) or 0.0)
                    
                    estimated_cost = price * int(order_details["quantity"])
                    
                    # Buffer: Ensure we have slightly more than the estimated cost
                    if estimated_cost > funds:
                        return f"Insufficient funds. Required approx {estimated_cost:.2f}, but you have {funds:.2f}."

            # 3. Route to specific logic
            if order_details.get("is_super_order"):
                return self._place_super_order_api(order_details)
            else:
                return self._place_normal_order_api(order_details)

        except Exception as e:
            print(f"[DhanHandler]: Critical Error: {e}")
            return "System error during order placement."

    # --- NORMAL ORDERS (Market/Limit + AMO) ---
    def _place_normal_order_api(self, od: dict) -> str:
        try:
            # Determine Price & Type
            # If MARKET, price sent to API must be 0
            is_limit = od.get("order_type") == "LIMIT"
            price_arg = float(od.get("price", 0.0)) if is_limit else 0.0
            
            # Determine AMO Status
            is_open = self.is_market_open()
            is_amo = not is_open  # If market closed, it's an AMO
            
            print(f"[Dhan]: Placing Normal Order. Type: {od.get('order_type')}, Price: {price_arg}, AMO: {is_amo}")

            response = self.dhan.place_order(
                security_id=str(od["security_id"]),
                exchange_segment=od["exchange_segment"],
                transaction_type=od["action"].upper(),
                quantity=int(od["quantity"]),
                order_type=od.get("order_type", "MARKET"),
                product_type="INTRADAY",
                price=price_arg,
                validity="DAY",
                after_market_order=is_amo
            )

            return self._parse_dhan_response(response, od, is_amo, is_super=False)

        except Exception as e:
            print(f"[Dhan]: Normal Order Error: {e}")
            return f"Failed to place normal order: {e}"

    # --- SUPER ORDERS (Bracket Orders) ---
    def _place_super_order_api(self, od: dict) -> str:
        """
        Manually hits the POST /super/orders endpoint.
        """
        try:
            url = f"{self.base_url}/super/orders"
            
            # Construct Payload per Documentation
            # Note: Super Orders usually don't accept 'afterMarketOrder' flag directly in same way
            payload = {
                "dhanClientId": self.client_id,
                "correlationId": f"voice_{int(datetime.datetime.now().timestamp())}",
                "transactionType": od["action"].upper(),
                "exchangeSegment": od["exchange_segment"],
                "productType": "INTRADAY", # Super orders usually Intraday
                "orderType": "LIMIT",      # Super orders are almost always LIMIT
                "securityId": str(od["security_id"]),
                "quantity": int(od["quantity"]),
                "price": float(od.get("price", 0.0)),
                "targetPrice": float(od["target_price"]),
                "stopLossPrice": float(od["stop_loss_price"]),
                "trailingJump": float(od.get("trailing_jump", 0.0))
            }

            print(f"[Dhan]: Placing SUPER Order: {payload}")
            
            response = requests.post(url, headers=self.headers, json=payload)
            data = response.json()
            
            return self._parse_dhan_response(data, od, is_amo=False, is_super=True)

        except Exception as e:
            print(f"[Dhan]: Super Order Error: {e}")
            return f"Failed to place super order: {e}"

    # --- RESPONSE PARSER ---
    def _parse_dhan_response(self, response: dict, details: dict, is_amo: bool, is_super: bool) -> str:
        status = response.get("status", "").lower()
        order_status = response.get("data", {}).get("orderStatus", "") if "data" in response else response.get("orderStatus", "")
        
        # Get stock name for clean output
        sym = details.get("symbol_name", details.get("symbol", "the stock"))

        if status == "success" or order_status in ["PENDING", "TRANSIT", "TRADED"]:
            if is_super:
                return f"Super Order for {sym} placed successfully."
            elif is_amo:
                return f"Market is closed. Order for {sym} placed as an After Market Order."
            else:
                return f"Order for {sym} executed successfully."
        
        elif status == "failure" or order_status == "REJECTED":
            # Extract error message
            remarks = response.get("remarks", {})
            error_msg = remarks.get("error_message", "Unknown reason")
            return f"The order was rejected by the broker. Reason: {error_msg}"
        
        else:
            return "Order received, but I couldn't verify the final status."
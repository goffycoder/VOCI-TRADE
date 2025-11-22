from dhanhq import dhanhq
import datetime
import pytz
import requests
import json

class DhanHandler:
    def __init__(self, client_id, access_token):
        """
        Initializes the Dhan API client.
        """
        self.client_id = client_id
        self.access_token = access_token
        self.base_url = "https://api.dhan.co/v2"
        
        # Headers for raw API calls (based on your docs)
        self.headers = {
            "access-token": access_token,
            "client-id": client_id,
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        try:
            # Keep existing library for order placement if it works well
            self.dhan = dhanhq(client_id, access_token)
            print("[DhanHandler]: Dhan client initialized successfully.")
        except Exception as e:
            print(f"[DhanHandler]: FATAL ERROR - Could not initialize Dhan client: {e}")
            raise

    # --- MARKET HOURS (Keep existing) ---
    def is_market_open(self) -> bool:
        try:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(tz)
            if now.weekday() >= 5: return False
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
            
            # Based on docs: "availabelBalance" (typo in their docs? we check both)
            # Docs say: availabelBalance
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
            
            # Handle if Dhan wraps it in a "data" key or returns a list directly
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
                # 'unrealizedProfit' is the current P&L for open positions
                pl = pos.get("unrealizedProfit", 0.0)
                total_pl += pl
                if pos.get("netQty", 0) != 0:
                    open_positions.append(f"{pos['tradingSymbol']} ({pl} rupees)")
            
            status = "profit" if total_pl >= 0 else "loss"
            pos_text = ", ".join(open_positions) if open_positions else "no open positions"
            
            return f"Total intraday P&L is a {status} of {abs(total_pl):.2f} rupees. Active positions: {pos_text}."
        
        except Exception as e:
            print(f"[DhanHandler]: Error fetching positions: {e}")
            return "I couldn't fetch your positions."

    # --- PHASE 3: LIVE MARKET DATA ---
    def get_live_price(self, security_id, exchange_segment="NSE_EQ"):
        """
        Fetches LTP (Last Traded Price) for a specific security.
        Docs: POST /marketfeed/ltp
        """
        try:
            url = f"{self.base_url}/marketfeed/ltp"
            # Docs require specific payload structure
            payload = {
                exchange_segment: [int(security_id)]
            }
            
            response = requests.post(url, headers=self.headers, json=payload)
            data = response.json()
            
            # Structure: data -> data -> NSE_EQ -> "security_id" -> last_price
            if data.get("status") == "success":
                market_data = data.get("data", {}).get(exchange_segment, {})
                instrument_data = market_data.get(str(security_id))
                if instrument_data:
                    return instrument_data.get("last_price")
            return None
        except Exception as e:
            print(f"[DhanHandler]: Error fetching price: {e}")
            return None

    # --- ORDER PLACEMENT (Modified for Funds Check) ---
    def place_voice_order(self, order_details: dict) -> str:
        try:
            # 1. Funds Check (if buying)
            if order_details["action"] == "BUY":
                funds = self.get_funds()
                if funds is not None:
                    # Estimate cost (Use provided price or fetch live price)
                    price = order_details.get("price")
                    if not price or price == 0.0:
                        # If market order, fetch current price to estimate
                        current_price = self.get_live_price(order_details["security_id"])
                        price = current_price if current_price else 0.0
                    
                    estimated_cost = price * order_details["quantity"]
                    if estimated_cost > funds:
                        return f"Insufficient funds. You have {funds} rupees, but this trade requires approx {estimated_cost} rupees."

            # 2. Existing Order Logic
            is_open = self.is_market_open()
            is_amo = not is_open
            
            price_arg = 0.0
            if order_details["order_type"] == "LIMIT":
                price_arg = float(order_details.get("price", 0.0))

            print(f"[DhanHandler]: Placing Order: {order_details}")
            
            # Use the existing library for placing orders (it's cleaner)
            order_response = self.dhan.place_order(
                security_id=order_details["security_id"],
                exchange_segment=order_details["exchange_segment"],
                transaction_type=order_details["action"],
                quantity=order_details["quantity"],
                order_type=order_details["order_type"],
                product_type="INTRADAY",
                price=price_arg,
                validity="DAY",
                after_market_order=is_amo
            )

            if order_response and order_response.get('status') == 'success':
                # Dynamic Success Message
                    if is_amo:
                        return f"Market is closed. Order for {order_details['symbol_name']} placed as an After Market Order."
                    else:
                     return f"Order for {order_details['symbol_name']} executed successfully."
            else:
                 return self._handle_error_response(order_response)

        except Exception as e:
            print(f"[DhanHandler]: Error: {e}")
            return "There was a system error placing the order."

    def _handle_error_response(self, order_response: dict) -> str:
        remarks = order_response.get('remarks', {})
        msg = remarks.get('error_message', 'Unknown error')
        return f"The broker rejected the order: {msg}"
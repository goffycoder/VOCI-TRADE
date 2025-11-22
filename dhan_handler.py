print("[DhanHandler]: Importing datetime/pytz...")
import datetime
import pytz # For time zone logic
print("[DhanHandler]: Imports done.")

class DhanHandler:
    def __init__(self, client_id, access_token):
        """
        Initializes the Dhan API client.
        """
        try:
            print("[DhanHandler]: Lazy importing dhanhq...")
            from dhanhq import dhanhq
            self.dhan = dhanhq(client_id, access_token)
            print("[DhanHandler]: Dhan client initialized successfully.")
        except Exception as e:
            print(f"[DhanHandler]: FATAL ERROR - Could not initialize Dhan client: {e}")
            # We don't raise here to allow the script to load for Simulation Mode check
            # But if we try to use it in Real Mode, it will fail later.
            self.dhan = None


    def is_market_open(self) -> bool:
        """
        Checks if the Indian market (NSE/BSE) is open.
        This is time-zone aware.
        """
        try:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.datetime.now(tz)
            
            # Market days are Monday (0) to Friday (4)
            if now.weekday() >= 5:
                print("[DhanHandler]: Market is CLOSED (Weekend)")
                return False
            
            # Market hours are 9:15 AM to 3:30 PM IST
            market_open = now.replace(hour=9, minute=15, second=0)
            market_close = now.replace(hour=15, minute=30, second=0)
            
            if market_open <= now <= market_close:
                print("[DhanHandler]: Market is OPEN")
                return True
            else:
                print("[DhanHandler]: Market is CLOSED (Outside trading hours)")
                return False
        except Exception as e:
            print(f"[DhanHandler]: Error checking market hours: {e}")
            return False # Default to 'closed' for safety

    def _handle_error_response(self, order_response: dict) -> str:
        """Translates a failed API response into plain English."""
        remarks = order_response.get('remarks', {})
        error_code = remarks.get('error_code')
        error_message = remarks.get('error_message', 'unknown error')

        print(f"[DhanHandler]: Order failed. Code: {error_code}, Message: {error_message}")

        # Specific, known error codes
        if error_code == "DH-905":
            return "The order failed. The broker said the Security ID was invalid."
        if error_code == "DH-900":
            return "Authentication failed. The API token is invalid or expired."
        
        # All other errors (like DH-906) will just return the server message
        return f"Sorry, the order failed. The broker said: {error_message}"

    def place_voice_order(self, order_details: dict) -> str:
        """
        Takes a final, validated order dictionary and places it.
        """
        try:
            is_open = self.is_market_open()
            is_amo = not is_open

            print(f"[DhanHandler]: Placing order with details: {order_details}")
            
            # --- THIS IS THE FIX ---
            # Set price to 0.0 for MARKET orders, otherwise use the provided price
            price = 0.0
            if order_details["order_type"] == "LIMIT":
                # Use .get() to safely handle None, though it should be a float
                price = float(order_details.get("price", 0.0))
            # --- END OF FIX ---
            
            order_response = self.dhan.place_order(
                security_id=order_details["security_id"],
                exchange_segment=order_details["exchange_segment"],
                transaction_type=order_details["action"],
                quantity=order_details["quantity"],
                order_type=order_details["order_type"],
                product_type="INTRADAY", # Hardcoded for safety
                price=price,             # This will now be 0.0 for MARKET
                validity="DAY",
                after_market_order=is_amo # <-- Correct AMO logic
            )
            
            print(f"[DhanHandler]: API Response: {order_response}")

            if order_response and order_response.get('status') == 'failure':
                return self._handle_error_response(order_response)

            elif order_response and order_response.get('status') == 'success':
                order_data = order_response.get('data', {})
                order_status = order_data.get('orderStatus', 'UNKNOWN')
                
                if order_status in ("TRANSIT", "PENDING"):
                    amo_msg = " as an after market order." if is_amo else "."
                    symbol_name = order_details.get("symbol_name", order_details.get("symbol"))
                    return (f"Your {order_details['action']} order for {order_details['quantity']} shares of "
                            f"{symbol_name} is in transit{amo_msg}")
                else:
                    return f"Your order was successful, but the status is {order_status}."
            
            else:
                return "An unknown error occurred. The API response was not recognized."

        except Exception as e:
            print(f"[DhanHandler]: An unexpected Python error occurred: {e}")
            return f"A system error occurred. Please check the logs."

    def get_fund_limit(self) -> float | None:
        """
        Retrieves the available balance in the trading account.
        Endpoint: GET /fundlimit
        """
        try:
            # Using the library method if available, otherwise we might need to check documentation for the exact method name.
            # Based on standard dhanhq library usage:
            response = self.dhan.get_fund_limits()
            if response['status'] == 'success':
                data = response['data']
                # Handle potential typo in API response as noted in docs ('availabelBalance')
                return float(data.get('availableBalance', data.get('availabelBalance', 0.0)))
            else:
                print(f"Dhan API Error (Fund Limit): {response.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error fetching fund limit: {e}")
            return None

    def get_order_margin(self, security_id: str, quantity: int, transaction_type: str, product_type: str, price: float = 0.0) -> float | None:
        """
        Calculates the total margin required for an order.
        Endpoint: POST /margincalculator
        """
        try:
            # Exchange segment is hardcoded to NSE_EQ for now as per current scope
            exchange_segment = "NSE_EQ" 
            
            # The library method for margin calculation. 
            # If the library doesn't have this exact method, we might fail. 
            # But assuming standard wrapper coverage.
            response = self.dhan.margin_calculator(
                security_id=security_id,
                exchange_segment=exchange_segment,
                transaction_type=transaction_type,
                quantity=quantity,
                product_type=product_type,
                price=price
            )
            
            if response['status'] == 'success':
                return float(response['data'].get('totalMargin', 0.0))
            else:
                print(f"Dhan API Error (Margin Calc): {response.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error calculating margin: {e}")
            return None

    def get_holdings(self) -> list | None:
        """
        Retrieves current holdings.
        Endpoint: GET /holdings
        """
        try:
            response = self.dhan.holdings()
            if response['status'] == 'success':
                return response['data']
            else:
                print(f"Dhan API Error (Holdings): {response.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error fetching holdings: {e}")
            return None

    def get_positions(self) -> list | None:
        """
        Retrieves current open positions.
        Endpoint: GET /positions
        """
        try:
            response = self.dhan.positions()
            if response['status'] == 'success':
                return response['data']
            else:
                print(f"Dhan API Error (Positions): {response.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error fetching positions: {e}")
            return None

    def fetch_ltp(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float | None:
        """
        Fetches the Last Traded Price (LTP) for a security.
        Endpoint: POST /marketfeed/ltp
        """
        try:
            # The library usually expects a specific format for LTP.
            # Based on common usage: dhan.ltp(exchange_segment, security_id)
            # We might need to pass it as a dictionary or arguments depending on the wrapper version.
            # Let's try the standard way.
            response = self.dhan.ltp(security_id, exchange_segment, "EQUITY") 
            
            if response['status'] == 'success':
                # The response structure for LTP usually contains 'data' -> 'last_price'
                # But sometimes it's nested under exchange/segment.
                # Let's inspect the response structure from docs:
                # { "data": { "NSE_EQ": { "11536": { "last_price": 4520 } } } }
                data = response['data']
                if exchange_segment in data and security_id in data[exchange_segment]:
                    return float(data[exchange_segment][security_id]['last_price'])
                else:
                    print(f"LTP not found in response: {data}")
                    return None
            else:
                print(f"Dhan API Error (LTP): {response.get('remarks', 'Unknown error')}")
                return None
        except Exception as e:
            print(f"Error fetching LTP: {e}")
            return None

    def convert_position(self, order_details: dict) -> str:
        """
        Converts an intraday position to delivery or vice versa.
        Endpoint: POST /positions/convert
        """
        try:
            # Assuming library usage: dhan.convert_position(security_id, exchange_segment, from_product, to_product, quantity, transaction_type)
            # We need to map the intent to these parameters.
            # For now, let's assume the user wants to convert 'INTRADAY' to 'CNC' (Delivery) or vice versa.
            # This might require more slot filling in main.py, but here we just wrap the call.
            
            # Hardcoding for simplicity of Phase 4: Convert INTRADAY -> CNC (Delivery)
            # In a real app, we'd ask "from what to what?".
            # Let's assume the user says "Convert X to delivery".
            
            from_product = "INTRADAY"
            to_product = "CNC" # Delivery
            
            response = self.dhan.convert_position(
                security_id=order_details['security_id'],
                exchange_segment=order_details.get('exchange_segment', 'NSE_EQ'),
                from_product_type=from_product,
                to_product_type=to_product,
                quantity=order_details['quantity'],
                transaction_type=order_details['action'] # BUY/SELL of the original position
            )
            
            if response['status'] == 'success':
                return "Position converted successfully."
            else:
                return f"Conversion failed: {response.get('remarks', {}).get('error_message', 'Unknown error')}"

        except Exception as e:
            print(f"Error converting position: {e}")
            return "System error during conversion."

    def square_off_all(self) -> str:
        """
        KILL SWITCH: Squares off all open positions.
        """
        try:
            positions = self.get_positions()
            if not positions:
                return "You have no open positions to close."
            
            open_positions = [p for p in positions if p.get('positionType') != 'CLOSED']
            if not open_positions:
                return "You have no open positions to close."
            
            success_count = 0
            fail_count = 0
            
            for pos in open_positions:
                # To square off, we place an opposing order.
                # Or use the library's square off method if available.
                # Standard way: Place MARKET order with opposite transaction type.
                
                security_id = pos['securityId']
                exchange_segment = pos['exchangeSegment']
                product_type = pos['productType']
                quantity = pos['netQty'] # This can be negative for SELL positions
                
                # Determine action needed to close
                if quantity > 0:
                    transaction_type = "SELL"
                    qty_to_trade = quantity
                elif quantity < 0:
                    transaction_type = "BUY"
                    qty_to_trade = abs(quantity)
                else:
                    continue # Should not happen for open positions
                
                print(f"[Kill Switch]: Closing {pos['tradingSymbol']} ({qty_to_trade} {transaction_type})")
                
                response = self.dhan.place_order(
                    security_id=security_id,
                    exchange_segment=exchange_segment,
                    transaction_type=transaction_type,
                    quantity=qty_to_trade,
                    order_type="MARKET",
                    product_type=product_type,
                    price=0.0,
                    validity="DAY"
                )
                
                if response['status'] == 'success':
                    success_count += 1
                else:
                    print(f"Failed to close {pos['tradingSymbol']}: {response}")
                    fail_count += 1
            
            return f"Kill switch executed. Closed {success_count} positions. Failed to close {fail_count}."

        except Exception as e:
            print(f"Error in Kill Switch: {e}")
            return "Critical error executing Kill Switch."
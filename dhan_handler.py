from dhanhq import dhanhq
from datetime import datetime
import pytz # For time zone logic

class DhanHandler:
    def __init__(self, client_id, access_token):
        """
        Initializes the Dhan API client.
        """
        try:
            self.dhan = dhanhq(client_id, access_token)
            print("[DhanHandler]: Dhan client initialized successfully.")
        except Exception as e:
            print(f"[DhanHandler]: Error initializing Dhan client: {e}")
            raise

    def _is_market_open(self) -> bool:
        """
        Checks if the Indian market (NSE/BSE) is open.
        This is time-zone aware.
        """
        try:
            tz = pytz.timezone('Asia/Kolkata')
            now = datetime.now(tz)
            
            # Market days are Monday (0) to Friday (4)
            if now.weekday() > 4:
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

        
        if error_code == "DH-905":
            return "The order failed. The broker said the Security ID was invalid."
        if error_code == "DH-900":
            return "Authentication failed. The API token is invalid or expired."
        return f"Sorry, the order failed. The broker said: {error_message}"

    def place_voice_order(self, order_details: dict) -> str:
        """
        Takes a final, validated order dictionary and places it.
        """
        try:
            is_open = self._is_market_open()
            is_amo = not is_open

            print(f"[DhanHandler]: Placing order with details: {order_details}")
            
            order_response = self.dhan.place_order(
                security_id=order_details["security_id"],
                exchange_segment="NSE_EQ", # Hardcoding NSE_EQ as requested
                transaction_type=order_details["action"],
                quantity=order_details["quantity"],
                order_type=order_details["order_type"],
                product_type="INTRADAY", # Hardcoded for safety
                price=order_details["price"],
                validity="DAY",
                after_market_order=is_amo # <-- NOW DYNAMIC
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
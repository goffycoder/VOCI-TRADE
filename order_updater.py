import json
import threading
import time
import sys

# Try importing websocket-client
try:
    import websocket
except ImportError:
    print("[OrderUpdate]: 'websocket-client' library not found. Order updates will be disabled.")
    websocket = None

from speech_service import say_text

class OrderUpdateListener:
    def __init__(self, client_id, access_token):
        self.client_id = client_id
        self.access_token = access_token
        self.ws_url = "wss://api-order-update.dhan.co"
        self.ws = None
        self.thread = None
        self.running = False

    def on_message(self, ws, message):
        try:
            # Message is JSON
            # The docs say response is JSON for Order Updates
            data = json.loads(message)
            
            # Check for Order Update
            # Structure: {"Data": {...}, "Type": "order_alert"}
            if data.get("Type") == "order_alert":
                order_data = data.get("Data", {})
                status = order_data.get("Status") # e.g., "TRADED", "PENDING", "REJECTED"
                symbol = order_data.get("DisplayName", order_data.get("Symbol", "Unknown Stock"))
                
                print(f"[OrderUpdate]: Received update for {symbol}: {status}")
                
                if status == "TRADED":
                    # Check if fully traded or partial? 
                    # Docs say "TradedQty" vs "Quantity". 
                    # But "Status": "TRADED" usually means fully done or at least a trade happened.
                    # We'll announce it.
                    say_text(f"Your order for {symbol} has been executed.")
                
                elif status == "REJECTED":
                     reason = order_data.get("ReasonDescription", "Unknown reason")
                     say_text(f"Your order for {symbol} was rejected. {reason}")
                     
        except Exception as e:
            print(f"[OrderUpdate]: Error parsing message: {e}")

    def on_error(self, ws, error):
        print(f"[OrderUpdate]: Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        print("[OrderUpdate]: Connection closed")
        # Optional: Reconnect logic could go here

    def on_open(self, ws):
        print("[OrderUpdate]: Connected. Sending Auth...")
        auth_msg = {
            "LoginReq": {
                "MsgCode": 42,
                "ClientId": self.client_id,
                "Token": self.access_token
            },
            "UserType": "SELF"
        }
        ws.send(json.dumps(auth_msg))

    def start(self):
        if not websocket:
            print("[OrderUpdate]: Cannot start listener (missing library).")
            return

        self.running = True
        # websocket.enableTrace(True) # Debugging
        self.ws = websocket.WebSocketApp(self.ws_url,
                                         on_open=self.on_open,
                                         on_message=self.on_message,
                                         on_error=self.on_error,
                                         on_close=self.on_close)
        
        self.thread = threading.Thread(target=self.ws.run_forever)
        self.thread.daemon = True # Kill thread when main app exits
        self.thread.start()
        print("[OrderUpdate]: Listener started in background.")

    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()

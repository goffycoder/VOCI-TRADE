class MockDhanHandler:
    def __init__(self, client_id, access_token):
        print("[MockDhanHandler]: Initialized in SIMULATION MODE.")
        self.dummy_balance = 10000000.0 # 1 Crore
        self.dummy_price = 100.0

    def get_fund_limit(self) -> float | None:
        print("[MockDhanHandler]: Returning dummy fund limit.")
        return self.dummy_balance

    def get_order_margin(self, security_id, quantity, transaction_type, product_type, price=0.0) -> float | None:
        print("[MockDhanHandler]: Calculating dummy margin.")
        # Simple logic: Price * Quantity
        # If price is 0 (Market), use dummy price
        calc_price = price if price > 0 else self.dummy_price
        return float(quantity) * calc_price

    def place_voice_order(self, order_details: dict) -> str:
        print(f"[MockDhanHandler]: Simulating order placement: {order_details}")
        symbol = order_details.get("symbol_name", order_details.get("symbol", "Unknown"))
        return f"SIMULATION: Your {order_details['action']} order for {order_details['quantity']} shares of {symbol} has been placed successfully."

    def get_holdings(self) -> list | None:
        print("[MockDhanHandler]: Returning dummy holdings.")
        return [
            {"tradingSymbol": "TCS", "totalQty": 10, "avgCostPrice": 3200.0},
            {"tradingSymbol": "RELIANCE", "totalQty": 5, "avgCostPrice": 2400.0}
        ]

    def get_positions(self) -> list | None:
        print("[MockDhanHandler]: Returning dummy positions.")
        return [
            {"tradingSymbol": "SBI", "netQty": 50, "positionType": "LONG", "exchangeSegment": "NSE_EQ", "securityId": "1333", "productType": "INTRADAY"},
            {"tradingSymbol": "INFY", "netQty": -20, "positionType": "SHORT", "exchangeSegment": "NSE_EQ", "securityId": "1594", "productType": "INTRADAY"}
        ]

    def fetch_ltp(self, security_id: str, exchange_segment: str = "NSE_EQ") -> float | None:
        print(f"[MockDhanHandler]: Returning dummy LTP for {security_id}.")
        return self.dummy_price

    def convert_position(self, order_details: dict) -> str:
        print(f"[MockDhanHandler]: Simulating position conversion: {order_details}")
        return "SIMULATION: Position converted successfully."

    def square_off_all(self) -> str:
        print("[MockDhanHandler]: Simulating Kill Switch.")
        return "SIMULATION: All positions have been squared off."

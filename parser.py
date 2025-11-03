# In parser.py
import re
from word2number import w2n

# --- 1. ALIAS MAPS ---
ACTION_ALIASES = {
    "buy": "BUY",
    "by": "BUY",
    "my": "BUY",
    "sell": "SELL",
    "cell": "SELL"
}

SYMBOL_ALIASES = {
    "RELIANCE": "RELIANCE",
    "AUDIENCE": "RELIANCE", 
    "RELY ON": "RELIANCE",
    "INFY": "INFOSYS",
    "INFOSYS": "INFOSYS",
    "TCS": "TCS",
    "ORIENT": "ORIENTCEM", 
}


def parse_voice_command(text: str) -> dict | None:
    """
    Parses a structured voice command using Regex, Aliases, and word2number.
    """
    print(f"[Parser]: Trying to parse: '{text}'")
    
    text = text.lower().replace("i'm listening", "").strip()

    # --- 2. The Robust Regex Pattern ---
    pattern = re.compile(
        # Group 1: Action
        r"(buy|by|my|sell|cell)\s+"
        
        # Group 2: Quantity
        r"([\w\s]+?)\s+"
        
        # Group 3: "share" or "shares"
        r"(share|shares)\s+of\s+"
        
        # Group 4: Stock Name
        r"([\w\s]+?)"
        
        # Group 5 (Optional): The price part (e.g., "one thousand")
        # NOTE: The outer group is (?:...) which is non-capturing
        r"(?:\s+at\s+([\w\s]+))?$"
    )
    
    match = pattern.search(text)

    if not match:
        print("[Parser]: Error. Command did not match the required pattern (ACTION QTY share/s of SYMBOL [at PRICE]).")
        return None

    # --- 3. Extract and Normalize Entities ---
    try:
        action_str = match.group(1)
        quantity_str = match.group(2).strip()
        stock_name_str = match.group(4).strip().upper()
        
        # --- THIS IS THE BUG FIX ---
        # The price is group 5, not 6.
        price_str = match.group(5) 
        # --- END OF BUG FIX ---

        parsed = {
            "action": None,
            "quantity": None,
            "symbol": None,
            "price": 0.0,
            "order_type": "MARKET"
        }

        # --- Normalize Action ---
        if action_str in ACTION_ALIASES:
            parsed["action"] = ACTION_ALIASES[action_str]
        else:
            print(f"[Parser]: Unknown action: '{action_str}'")
            return None

        # --- Normalize Quantity ---
        try:
            parsed["quantity"] = w2n(quantity_str)
        except ValueError:
            print(f"[Parser]: Could not understand quantity: '{quantity_str}'")
            return None

        # --- Normalize Symbol ---
        if stock_name_str in SYMBOL_ALIASES:
            parsed["symbol"] = SYMBOL_ALIASES[stock_name_str]
        else:
            print(f"[Parser]: Unknown stock alias: '{stock_name_str}'. Add it to SYMBOL_ALIASES.")
            return None

        # --- Normalize Price ---
        if price_str: # This will be None if "at..." wasn't said
            try:
                parsed["price"] = float(w2n(price_str.strip()))
                parsed["order_type"] = "LIMIT"
            except ValueError:
                print(f"[Parser]: Understood 'at' but not the price: '{price_str}'")
                parsed["order_type"] = "MARKET" 

        print(f"[Parser]: Success! -> {parsed}")
        return parsed

    except Exception as e:
        print(f"[Parser]: Error during extraction: {e}")
        return None
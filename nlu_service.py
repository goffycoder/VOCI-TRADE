import os
import json
import google.generativeai as genai

# --- 1. Initialize Gemini Client ---
try:
    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("FATAL ERROR: GOOGLE_API_KEY not found in .env file.")
        exit()
    
    genai.configure(api_key=GOOGLE_API_KEY)
    gemini_model = genai.GenerativeModel('models/gemini-flash-latest')
    print("[Gemini NLU]: Client initialized.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Gemini: {e}")
    exit()

# --- 2. NLU Functions ---
def get_order_intent_gemini(transcription: str) -> dict | None:
    """
    Uses Gemini to parse the initial command with enhanced prompt engineering.
    """
    prompt = f"""
You are an expert NLU system for a stock trading voice assistant.

TASK: Extract trading order details, portfolio/price queries, or position management commands.

OUTPUT FORMAT: Valid JSON object with these fields:
{{
  "intent": "ORDER" or "GET_PORTFOLIO" or "GET_PRICE" or "CONVERT_POSITION" or "KILL_SWITCH",
  "action": "BUY" or "SELL" or null,
  "quantity": integer or null,
  "symbol": "spoken stock name" or null,
  "price": float or null,
  "order_type": "MARKET" or "LIMIT" or null
}}

RULES:
1. "intent": 
   - "GET_PORTFOLIO": "what do I own", "show holdings", "my positions".
   - "GET_PRICE": "what is the price of X", "current rate of X".
   - "CONVERT_POSITION": "convert X to delivery", "change X to intraday".
   - "KILL_SWITCH": "close everything", "square off all", "panic mode", "exit all".
   - "ORDER": buy/sell/trade commands.
2. "action": Extract only if user says "buy", "sell", "purchase", "acquire", "short", etc.
3. "quantity": Extract numbers like "five", "100", "fifty shares", "10 units"
4. "symbol": Extract company names like "reliance", "tata motors", "infosys"
   - Include partial names: "tata" is valid
   - Include abbreviations: "tcs" is valid
5. "price": Extract if user mentions price: "at 1500", "for 2000 rupees"
6. "order_type": 
   - "LIMIT" if price is mentioned
   - "MARKET" if no price mentioned AND action is present
   - null if action is not present
7. Set ANY field to null if not explicitly mentioned
8. DO NOT guess or infer missing information

EXAMPLES:
User: "buy 10 reliance"
Output: {{"intent": "ORDER", "action": "BUY", "quantity": 10, "symbol": "reliance", "price": null, "order_type": "MARKET"}}

User: "what do I have in my portfolio"
Output: {{"intent": "GET_PORTFOLIO", "action": null, "quantity": null, "symbol": null, "price": null, "order_type": null}}

User: "what is the price of tcs"
Output: {{"intent": "GET_PRICE", "action": null, "quantity": null, "symbol": "tcs", "price": null, "order_type": null}}

User: "convert 50 shares of sbi to delivery"
Output: {{"intent": "CONVERT_POSITION", "action": null, "quantity": 50, "symbol": "sbi", "price": null, "order_type": null}}

User: "close all my positions immediately"
Output: {{"intent": "KILL_SWITCH", "action": null, "quantity": null, "symbol": null, "price": null, "order_type": null}}

USER COMMAND: "{transcription}"

JSON OUTPUT:
"""
    
    print(f"[NLU]: Analyzing command: '{transcription}'")
    response = None
    
    try:
        response = gemini_model.generate_content(prompt)
        json_string = response.text.strip()
        
        # Remove markdown code blocks if present
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.startswith("```"):
            json_string = json_string[3:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]
        
        json_string = json_string.strip()
        
        result = json.loads(json_string)
        print(f"[NLU]: ✓ Parsed: action={result.get('action')}, qty={result.get('quantity')}, symbol={result.get('symbol')}")
        return result
        
    except json.JSONDecodeError as e:
        response_text = response.text if response else "No response"
        print(f"[NLU]: ✗ JSON Parse Error: {e}")
        print(f"[NLU]: Raw response: {response_text}")
        return None
    except Exception as e:
        response_text = response.text if response else "No response"
        print(f"[NLU]: ✗ Error: {e} | Response: {response_text}")
        return None


def fill_missing_slot_gemini(pending_order: dict, follow_up_answer: str, missing_slot: str) -> dict | None:
    """
    Uses Gemini to extract a single missing piece of information.
    """
    prompt = f"""
You are a slot-filling assistant for a stock trading system.

CONTEXT: User's partial order:
{json.dumps(pending_order, indent=2)}

MISSING INFORMATION: "{missing_slot}"

USER'S ANSWER: "{follow_up_answer}"

TASK: Extract ONLY the "{missing_slot}" value from the user's answer.

EXTRACTION RULES:
- If missing_slot is "action": Extract "BUY" or "SELL"
  Examples: "buy" → "BUY", "sell it" → "SELL", "purchase" → "BUY"
  
- If missing_slot is "quantity": Extract integer
  Examples: "five" → 5, "100 shares" → 100, "fifty" → 50
  
- If missing_slot is "symbol": Extract stock name exactly as spoken
  Examples: "reliance" → "reliance", "tata motors" → "tata motors"
  
- If missing_slot is "price": Extract float
  Examples: "1500" → 1500.0, "at 2000" → 2000.0

OUTPUT FORMAT: Valid JSON with ONLY the extracted field:
{{
  "{missing_slot}": "EXTRACTED_VALUE"
}}

EXAMPLES:
Missing: "action", Answer: "I want to buy" → {{"action": "BUY"}}
Missing: "quantity", Answer: "fifty shares" → {{"quantity": 50}}
Missing: "symbol", Answer: "tata motors" → {{"symbol": "tata motors"}}

JSON OUTPUT:
"""
    
    print(f"[NLU Slot-Fill]: Extracting '{missing_slot}' from: '{follow_up_answer}'")
    response = None
    
    try:
        response = gemini_model.generate_content(prompt)
        json_string = response.text.strip()
        
        # Remove markdown code blocks
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.startswith("```"):
            json_string = json_string[3:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]
        
        json_string = json_string.strip()
        
        result = json.loads(json_string)
        
        if missing_slot in result and result[missing_slot] is not None:
            print(f"[NLU Slot-Fill]: ✓ Extracted {missing_slot}={result[missing_slot]}")
            return result
        else:
            print(f"[NLU Slot-Fill]: ✗ Failed to extract '{missing_slot}'")
            return None
            
    except json.JSONDecodeError as e:
        response_text = response.text if response else "No response"
        print(f"[NLU Slot-Fill]: ✗ JSON Parse Error: {e}")
        print(f"[NLU Slot-Fill]: Raw response: {response_text}")
        return None
    except Exception as e:
        response_text = response.text if response else "No response"
        print(f"[NLU Slot-Fill]: ✗ Error: {e} | Response: {response_text}")
        return None


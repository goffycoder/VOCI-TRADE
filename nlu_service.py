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
    Parses natural language into a structured order dictionary.
    Supports Market, Limit, and Super Orders.
    """
    prompt = f"""
You are an expert NLU system for a stock trading voice assistant.

TASK: Extract trading order details from the user's spoken command.

OUTPUT FORMAT: Valid JSON object with these fields:
{{
  "action": "BUY" | "SELL" | null,
  "quantity": integer | null,
  "symbol": "string" | null,
  "price": float | null,              # Limit Price (if user says "at 500")
  "order_type": "MARKET" | "LIMIT",   # Default to MARKET if no price mentioned
  "is_super_order": boolean,          # True if Target or Stop Loss is mentioned
  "target_price": float | null,       # For Super Order (Target/Profit)
  "stop_loss_price": float | null,    # For Super Order (Stop Loss)
  "trailing_jump": float | null       # For Super Order (Trailing Stop)
}}

RULES:
1. "action": Extract only if user says "buy", "sell", "purchase", "acquire", "short", etc.
2. "quantity": Extract numbers like "five", "100", "fifty shares", "10 units"
3. "symbol": Extract company names like "reliance", "tata motors", "infosys"
   - Include partial names: "tata" is valid
   - Include abbreviations: "tcs" is valid
4. "price": Extract if user mentions price: "at 1500", "for 2000 rupees"
5. "order_type": 
   - "LIMIT" if price is mentioned
   - "MARKET" if no price mentioned AND action is present
   - null if action is not present
6. Set ANY field to null if not explicitly mentioned
7. DO NOT guess or infer missing information
8. If user says "at [price]", set "price" and "order_type": "LIMIT".
9. If user mentions "target", "profit", or "stop loss", set "is_super_order": true.
10. If no price is mentioned, set "order_type": "MARKET" and "price": 0.0.


EXAMPLES:
"Buy 10 Reliance" -> {{"action": "BUY", "quantity": 10, "symbol": "Reliance", "order_type": "MARKET", "is_super_order": false}}
"Sell 50 Tata Motors at 950" -> {{"action": "SELL", "quantity": 50, "symbol": "Tata Motors", "price": 950.0, "order_type": "LIMIT", "is_super_order": false}}
"Buy 100 HDFC at 1500 with target 1600 and stop loss 1400" -> {{"action": "BUY", "quantity": 100, "symbol": "HDFC", "price": 1500.0, "order_type": "LIMIT", "is_super_order": true, "target_price": 1600.0, "stop_loss_price": 1400.0}}

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

def translate_if_needed(text: str) -> str:
    """
    Detects if text is non-English (specifically Hindi/Hinglish) and translates to English.
    Returns original text if already English.
    """
    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    Analyze the following text: "{text}"
    
    If it is in Hindi or Hinglish (Hindi written in English), translate it to a clear English trading command.
    If it is already in English, return the original text exactly.
    
    Examples:
    "Reliance ka price kya hai" -> "What is the price of Reliance"
    "10 share kharido Tata Motors ke" -> "Buy 10 shares of Tata Motors"
    "Market kaisa hai" -> "Show market news"
    "Mere holdings dikhao" -> "Show my holdings"
    "Show me the price of TCS" -> "Show me the price of TCS"
    
    Output ONLY the translated English text (or original). No explanations.
    """
    
    try:
        response = model.generate_content(prompt)
        translated = response.text.strip()
        if translated.lower() != text.lower():
            print(f"[Translation]: {text} -> {translated}")
        return translated
    except Exception as e:
        print(f"Translation Error: {e}")
        return text

def get_general_intent(transcription: str) -> str:
    """
    Determines the general intent of a user's command using Gemini.
    """
    prompt = f"""
You are an NLU system for a stock trading voice assistant.
Your task is to classify the user's command into one of the following intents:
- MARKET_NEWS: User wants to know about market news, headlines, or general market updates.
- PLACE_ORDER: User wants to buy or sell stocks.
- GET_HOLDINGS: User wants to see their current stock holdings.
- GET_POSITIONS: User wants to see their open trading positions.
- GET_FUNDS: User wants to know their available funds or balance.
- CHECK_PRICE: User wants to know the price of a specific stock.
- UNKNOWN: The intent cannot be determined from the given command.

RULES:
- Be strict with classification. If unsure, classify as UNKNOWN.
- Output ONLY the intent name in uppercase.

EXAMPLES:
"What's the news today?" -> MARKET_NEWS
"Buy 10 shares of Reliance" -> PLACE_ORDER
"Sell Tata Motors" -> PLACE_ORDER
"Show me my portfolio" -> GET_HOLDINGS
"What are my current positions?" -> GET_POSITIONS
"How much money do I have?" -> GET_FUNDS
"What is the price of HDFC?" -> CHECK_PRICE
"Tell me a joke" -> UNKNOWN
"Hello" -> UNKNOWN

USER COMMAND: "{transcription}"

INTENT:
"""
    try:
        response = gemini_model.generate_content(prompt)
        intent = response.text.strip().upper()
        valid_intents = ["MARKET_NEWS", "PLACE_ORDER", "GET_HOLDINGS", "GET_POSITIONS", "GET_FUNDS", "CHECK_PRICE", "UNKNOWN"]
        return intent if intent in valid_intents else "UNKNOWN"
    except Exception:
        return "UNKNOWN"

def analyze_news_sentiment(headlines: list[str]) -> str:
    """
    Analyzes headlines and returns a concise summary with sentiment.
    """
    headlines_text = "\n".join([f"- {h}" for h in headlines])
    
    prompt = f"""
    Analyze these news headlines for the Indian Stock Market:
    {headlines_text}
    
    1. Provide a very brief summary (2 sentences max).
    2. Determine the overall sentiment: POSITIVE, NEGATIVE, or NEUTRAL.
    
    Output format: "Summary... [Sentiment]"
    """
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception:
        return "I couldn't analyze the news right now."

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

def extract_news_topic(text: str) -> str:
    """
    Extracts the specific company, index, or topic for news search.
    Defaults to 'Indian Stock Market' if no specific topic is found.
    """
    prompt = f"""
    You are an entity extractor for a stock market news bot.
    
    TASK: Identify the specific company, stock symbol, sector, or topic the user wants news about.
    
    RULES:
    1. If the user mentions a specific name (e.g., "HDFC", "Zomato", "Bank Nifty", "IT Sector"), return that name.
    2. If the user asks generically (e.g., "market news", "what is happening", "latest updates"), return "Indian Stock Market".
    3. Append "Share Price India" to company names to ensure financial news results.
    
    EXAMPLES:
    User: "Tell me news about Reliance" -> "Reliance Industries Share Price India"
    User: "What is happening with Zomato?" -> "Zomato Share Price India"
    User: "Any news on Tata Motors?" -> "Tata Motors Share Price India"
    User: "Give me the market headlines" -> "Indian Stock Market"
    User: "News for HDFC Bank" -> "HDFC Bank Share Price India"
    
    USER INPUT: "{text}"
    
    OUTPUT (Just the string):
    """
    try:
        # Assuming 'gemini_model' is initialized globally in this file as per your previous code
        response = gemini_model.generate_content(prompt)
        topic = response.text.strip()
        # clean up any quotes or extra formatting
        topic = topic.replace('"', '').replace("'", "").strip()
        return topic
    except Exception as e:
        print(f"[NLU]: Error extracting news topic: {e}")
        return "Indian Stock Market"
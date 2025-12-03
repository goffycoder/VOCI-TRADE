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
1. If single order: Return the object directly.
2. If multiple orders: Return {{ "orders": [order1, order2] }}
3. If "Close all positions" / "Square off": Return {{ "action": "SQUARE_OFF_ALL" }}

SPECIAL RULES:
- "quantity": If user says "max", "all my funds", "full capital" -> set "quantity": "MAX"
- "quantity": If user says "sell all shares of X" -> set "quantity": "ALL"
- "action": "SQUARE_OFF_ALL" is only for "Sell everything", "Close all positions".

EXAMPLES:
"Buy max shares of Reliance" -> {{ "action": "BUY", "quantity": "MAX", "symbol": "Reliance", "order_type": "MARKET" }}
"Buy 10 TCS and Sell 5 Infosys" -> {{ "orders": [{{ "action": "BUY", "quantity": 10, "symbol": "TCS" }}, {{ "action": "SELL", "quantity": 5, "symbol": "Infosys" }}] }}
"Close all my positions" -> {{ "action": "SQUARE_OFF_ALL" }}

USER COMMAND: "{transcription}"

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
    Determines the intent. Defaults to CONVERSATIONAL if no specific trading action is found.
    """
    prompt = f"""
You are an NLU router for a stock trading voice assistant.

TASK: Classify the user command into one of these SPECIFIC intents:

1. MARKET_NEWS: User asks for news, headlines, updates on specific stocks or the market.
2. PLACE_ORDER: User explicitly wants to BUY, SELL, SQUARE OFF, or CLOSE positions.
3. GET_HOLDINGS: User wants to see their portfolio, holdings, or long-term investments.
4. GET_POSITIONS: User wants to see intraday/open positions or P&L.
5. GET_ORDERS: User wants to see PENDING orders or non-executed orders.
6. CHECK_MARGIN: User asks "How much margin/funds/money needed for X?".
7. GET_FUNDS: User asks about balance, funds, or money available.
8. CHECK_PRICE: User asks for the price/quote of a specific stock.
9. CONVERSATIONAL: EVERYTHING ELSE. Includes:
   - Educational questions ("What is an index?", "How do options work?")
   - General market discussions ("Why is the market down?")
   - Greetings ("Hello")
   - Unclear or vague inputs.

RULES:
- Do NOT output "UNKNOWN". If it doesn't fit intents 1-6, it is CONVERSATIONAL.
- Output ONLY the intent name in uppercase.

EXAMPLES:
"Buy 10 Reliance" -> PLACE_ORDER
"What is the price of Tata?" -> CHECK_PRICE
"Show my portfolio" -> GET_HOLDINGS
"Show my pending orders" -> GET_ORDERS
"How much margin for Reliance?" -> CHECK_MARGIN
"I want to learn about the stock market" -> CONVERSATIONAL
"What is an index?" -> CONVERSATIONAL
"Hello" -> CONVERSATIONAL

USER COMMAND: "{transcription}"

INTENT:
"""
    try:
        response = gemini_model.generate_content(prompt)
        intent = response.text.strip().upper()
        # Clean potential markdown
        intent = intent.replace("```", "").strip()
        
        valid_intents = [
            "MARKET_NEWS", "PLACE_ORDER", "GET_HOLDINGS", "GET_POSITIONS", 
            "GET_FUNDS", "CHECK_PRICE", "CONVERSATIONAL", "GET_ORDERS", "CHECK_MARGIN"
        ]
        
        if intent in valid_intents:
            return intent
        else:
            return "CONVERSATIONAL" # Fallback to chat instead of error
    except Exception:
        return "CONVERSATIONAL" # Fallback on error

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
    Intelligently merges new information from the user into the pending order.
    It extracts ANY order details found in the answer, not just the missing slot.
    Also handles STT corrections (e.g., "Cell" -> "SELL").
    """
    prompt = f"""
You are a smart context-updater for a trading bot.

CURRENT ORDER STATE:
{json.dumps(pending_order, indent=2)}

SYSTEM ASKED FOR: "{missing_slot}"
USER ANSWERED: "{follow_up_answer}"

TASK: 
1. Update the order with information provided in the "USER ANSWER".
2. Extract NOT ONLY the missing slot, but ANY other order details (Action, Quantity, Symbol, Price) provided.
3. Fix phonetic typos (e.g., "Cell" -> "SELL", "Eye" -> "BUY", "share" -> quantity).

RULES:
- Update "action" if user says "buy", "sell", "short", "purchase", "cell" (typo).
- Update "quantity" if user mentions numbers or "shares".
- Update "symbol" if user names a stock.
- Keep existing values in CURRENT ORDER STATE unless the user explicitly overrides them.

OUTPUT FORMAT:
Return a JSON object containing the NEWLY EXTRACTED or UPDATED fields only.

EXAMPLES:
1. Context: {{ "action": "BUY" }}, User: "Reliance", Output: {{ "symbol": "Reliance" }}
2. Context: {{ }}, User: "Cell 10 shares of Tata", Output: {{ "action": "SELL", "quantity": 10, "symbol": "Tata" }}
3. Context: {{ "symbol": "TCS" }}, User: "Buy 5", Output: {{ "action": "BUY", "quantity": 5 }}

JSON OUTPUT:
"""
    
    print(f"[NLU Context Update]: Analyzing answer: '{follow_up_answer}'")
    
    try:
        response = gemini_model.generate_content(prompt)
        json_string = response.text.strip()
        
        # Clean Markdown
        if json_string.startswith("```json"): json_string = json_string[7:]
        if json_string.startswith("```"): json_string = json_string[3:]
        if json_string.endswith("```"): json_string = json_string[:-3]
        
        result = json.loads(json_string.strip())
        print(f"[NLU Context Update]: ✓ Merged Data: {result}")
        return result
            
    except Exception as e:
        print(f"[NLU Context Update]: ✗ Error: {e}")
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
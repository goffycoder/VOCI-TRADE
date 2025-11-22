from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import base64
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import services
from nlu_service import get_general_intent, get_order_intent_gemini, analyze_news_sentiment, fill_missing_slot_gemini
from speech_service import generate_audio_bytes
from dhan_handler import DhanHandler
from stock_finder import StockFinder
from news_service import get_latest_market_news

# Initialize App & Handlers
app = FastAPI()

# Global State for Logic Handlers
dhan_api = None
stock_finder = None

# Initialize Logic Handlers on Startup
try:
    dhan_api = DhanHandler(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))
    stock_finder = StockFinder()
    print("[Server]: Services initialized successfully.")
except Exception as e:
    print(f"[Server]: FATAL INIT ERROR: {e}")

# --- Data Models ---
class UserRequest(BaseModel):
    message: str
    # Context helps us track if we are inside a specific conversation flow
    context: dict = {} 

class BotResponse(BaseModel):
    text: str
    audio_base64: str # Base64 encoded audio for browser to play
    data: dict = {}   # Any extra data (like stock price to display on UI)

# --- Logic Helper ---
def process_command(text: str, context: dict) -> tuple[str, dict]:
    """
    Main logic router. Returns (response_text, response_data).
    """
    # 1. Classify Intent
    intent = get_general_intent(text)
    print(f"[Logic]: Intent Detected -> {intent}")

    response_text = ""
    response_data = {"intent": intent}
    
    # --- HANDLER: MARKET NEWS ---
    if intent == "MARKET_NEWS":
        query = "Indian Stock Market" 
        if "reliance" in text.lower(): query = "Reliance Industries"
        if "adani" in text.lower(): query = "Adani Group"
        if "tata" in text.lower(): query = "Tata Group"
        
        headlines = get_latest_market_news(query)
        if headlines:
            summary = analyze_news_sentiment(headlines)
            response_text = f"Here is the latest news for {query}. {summary}"
        else:
            response_text = f"I couldn't find any recent news for {query}."

    # --- HANDLER: CHECK FUNDS (Phase 1) ---
    elif intent == "GET_FUNDS":
        funds = dhan_api.get_funds()
        if funds is not None:
            response_text = f"You have {funds:,.2f} rupees available in your trading account."
        else:
            response_text = "I was unable to fetch your balance details from the broker."

    # --- HANDLER: PORTFOLIO HOLDINGS (Phase 2) ---
    elif intent == "GET_HOLDINGS":
        response_text = dhan_api.get_holdings_summary()

    # --- HANDLER: OPEN POSITIONS (Phase 2) ---
    elif intent == "GET_POSITIONS":
        response_text = dhan_api.get_positions_summary()

    # --- HANDLER: CHECK PRICE (Phase 3) ---
    elif intent == "CHECK_PRICE":
        # We reuse the NLU to extract the stock symbol from the question
        extraction = get_order_intent_gemini(text)
        symbol = extraction.get("symbol") if extraction else None
        
        if symbol:
            # Find the ID
            id_results = stock_finder.find_security_id(symbol)
            if id_results:
                # Take the first best match
                sec_id, name = id_results[0]
                price = dhan_api.get_live_price(sec_id)
                
                if price:
                    response_text = f"The current price of {name} is {price} rupees."
                    response_data["price"] = price
                    response_data["symbol"] = name
                else:
                    response_text = f"I found {name}, but the live price data is currently unavailable."
            else:
                response_text = f"Sorry, I couldn't find a stock named {symbol} in the database."
        else:
            response_text = "I'm not sure which stock you are asking about."

    # --- HANDLER: PLACE ORDER (Phase 1 + Logic) ---
    elif intent == "PLACE_ORDER":
        order_data = get_order_intent_gemini(text)
        if order_data and order_data.get("symbol"):
            symbol = order_data["symbol"]
            
            # Resolve Symbol to Security ID
            id_results = stock_finder.find_security_id(symbol)
            
            if not id_results:
                response_text = f"I couldn't find the stock {symbol}. Order cancelled."
            elif len(id_results) > 1:
                # (Simple disambiguation for V1: Pick the first one)
                # In V2, we will ask the user to clarify
                sec_id, name = id_results[0]
                order_data["security_id"] = sec_id
                order_data["symbol_name"] = name
                order_data["exchange_segment"] = "NSE_EQ" # Defaulting to NSE Equity
                
                # Execute the order (DhanHandler now checks funds internally)
                response_text = dhan_api.place_voice_order(order_data)
            else:
                # Exact match
                sec_id, name = id_results[0]
                order_data["security_id"] = sec_id
                order_data["exchange_segment"] = "NSE_EQ"
                response_text = dhan_api.place_voice_order(order_data)
        else:
            response_text = "I didn't quite catch the order details. Please try saying 'Buy 10 shares of Reliance'."

    # --- FALLBACK ---
    else:
        response_text = "I'm listening. You can check prices, funds, holdings, or place an order."

    return response_text, response_data

# --- API Endpoint ---
@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(request: UserRequest):
    """
    Receives text (from browser STT), processes logic, returns text + audio.
    """
    user_text = request.message
    context = request.context
    
    # 1. Process Logic
    reply_text, reply_data = process_command(user_text, context)
    
    # 2. Generate Audio (ElevenLabs)
    # Note: If reply_text is empty/error, we send a default audio
    audio_bytes = generate_audio_bytes(reply_text)
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return BotResponse(
        text=reply_text,
        audio_base64=audio_b64,
        data=reply_data
    )

if __name__ == "__main__":
    print("Starting Voice Trader Server...")
    # 0.0.0.0 allows connection from other devices on the network (like your phone/frontend)
    uvicorn.run(app, host="0.0.0.0", port=8000)
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

# Initialize Logic Handlers
try:
    dhan_api = DhanHandler(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))
    stock_finder = StockFinder()
except Exception as e:
    print(f"Server Init Error: {e}")

# --- Data Models ---
class UserRequest(BaseModel):
    message: str
    # We can pass client-side state here later (e.g., current_order context)
    context: dict = {} 

class BotResponse(BaseModel):
    text: str
    audio_base64: str # Base64 encoded audio for browser to play
    data: dict = {}   # Any extra data (like stock price to display)

# --- Logic Helper ---
def process_command(text: str, context: dict):
    """
    Main logic router.
    """
    # 1. Check if we are in the middle of an order flow (Context Check)
    if context.get("status") == "awaiting_slot":
        # Handle slot filling (Logic to be migrated from main.py later)
        # For now, let's keep it simple: Reset if user changes topic
        pass 

    # 2. Classify Intent
    intent = get_general_intent(text)
    print(f"Intent Detected: {intent}")

    response_text = ""
    
    if intent == "MARKET_NEWS":
        # Extract entity (simple heuristic or use Gemini again)
        query = "Indian Stock Market" 
        if "reliance" in text.lower(): query = "Reliance Industries"
        if "adani" in text.lower(): query = "Adani Group"
        
        headlines = get_latest_market_news(query)
        if headlines:
            summary = analyze_news_sentiment(headlines)
            response_text = f"Here is the latest news for {query}. {summary}"
        else:
            response_text = f"I couldn't find any recent news for {query}."

    elif intent == "PLACE_ORDER":
        order_data = get_order_intent_gemini(text)
        if order_data:
            # (Simplified flow for V1 server - full flow needs state management)
            response_text = f"I understood you want to {order_data.get('action')} {order_data.get('quantity')} shares of {order_data.get('symbol')}. I need to connect the Order Manager to this server next."
        else:
            response_text = "I didn't quite catch the order details."

    elif intent == "GET_HOLDINGS":
        # Call Dhan API
        # (Future integration)
        response_text = "I can fetch your holdings, but I need to verify your PIN first."

    else:
        # Fallback chat
        response_text = "I'm listening. You can ask for news, holdings, or place an order."

    return response_text

# --- API Endpoint ---
@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(request: UserRequest):
    """
    Receives text (from browser STT), processes logic, returns text + audio.
    """
    user_text = request.message
    context = request.context
    
    # 1. Process Logic
    reply_text = process_command(user_text, context)
    
    # 2. Generate Audio (ElevenLabs)
    audio_bytes = generate_audio_bytes(reply_text)
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return BotResponse(
        text=reply_text,
        audio_base64=audio_b64,
        data={"intent": "unknown"} # Can send debug info back
    )

if __name__ == "__main__":
    print("Starting Voice Trader Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
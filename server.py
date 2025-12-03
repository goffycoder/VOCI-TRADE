from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
import uvicorn
import base64
import os
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# Import services
from nlu_service import (
    get_general_intent, 
    get_order_intent_gemini, 
    analyze_news_sentiment,  
    fill_missing_slot_gemini, 
    extract_news_topic
)
from speech_service import generate_audio_bytes
from dhan_handler import DhanHandler
from stock_finder import StockFinder
from news_service import get_latest_market_news
from news_service import get_latest_market_news

# Initialize App & Handlers
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global State for Logic Handlers
dhan_api = None
stock_finder = None

try:
    dhan_api = DhanHandler(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))
    stock_finder = StockFinder()
    print("[Server]: Services initialized successfully.")
except Exception as e:
    print(f"[Server]: FATAL INIT ERROR: {e}")

# --- Data Models ---
class UserRequest(BaseModel):
    message: str
    context: dict = {} # Stores the "Memory" of the conversation

class BotResponse(BaseModel):
    text: str
    audio_base64: str
    data: dict = {}

# --- HELPER: Validation & Execution Loop ---
def validate_and_execute_order(order_data: dict) -> tuple[str, dict]:
    """
    Checks if order has Action, Quantity, and Symbol/SecID.
    - If missing: returns a QUESTION + CONTEXT.
    - If complete: executes order + returns RESULT.
    """
    # 1. Check Symbol
    if not order_data.get("symbol") and not order_data.get("security_id"):
        return "Which stock do you want to trade?", {
            "status": "WAITING_FOR_SLOT",
            "missing_slot": "symbol",
            "pending_order": order_data
        }

    # 2. Check Action (Buy/Sell)
    if not order_data.get("action"):
        stock_name = order_data.get('symbol', 'the stock')
        return f"Do you want to Buy or Sell {stock_name}?", {
            "status": "WAITING_FOR_SLOT",
            "missing_slot": "action",
            "pending_order": order_data
        }

    # 3. Check Quantity
    if not order_data.get("quantity"):
        stock_name = order_data.get('symbol_name', order_data.get('symbol', 'it'))
        return f"How many shares of {stock_name}?", {
            "status": "WAITING_FOR_SLOT",
            "missing_slot": "quantity",
            "pending_order": order_data
        }
    
    if order_data.get("is_super_order"):
        if not order_data.get("target_price"):
            return "What is your Target Profit price?", {
                "status": "WAITING_FOR_SLOT", 
                "missing_slot": "target_price", 
                "pending_order": order_data
            }
        if not order_data.get("stop_loss_price"):
            return "What is your Stop Loss price?", {
                "status": "WAITING_FOR_SLOT", 
                "missing_slot": "stop_loss_price", 
                "pending_order": order_data
            }
        
    # 4. All Good -> Execute
    print(f"[Logic]: Order Complete. Executing -> {order_data}")
    # Note: DhanHandler's place_voice_order now handles the Funds Check internally
    result_text = dhan_api.place_voice_order(order_data)
    
    # Return success and CLEAR the context
    return result_text, {"intent": "ORDER_RESULT", "status": "COMPLETE"}

# --- MAIN LOGIC ROUTER ---
def process_command(text: str, context: dict) -> tuple[str, dict]:
    
    # --- 1. CONTEXT CHECK (Are we in the middle of a question?) ---
    if context and context.get("status") == "WAITING_FOR_SLOT":
        pending_order = context.get("pending_order", {})
        missing_slot = context.get("missing_slot")
        
        print(f"[Logic]: User answered slot '{missing_slot}' with: '{text}'")
        
        # Use Gemini to extract just the missing piece (e.g., "50" -> 50)
        extracted_data = fill_missing_slot_gemini(pending_order, text, missing_slot)
        
        if extracted_data and extracted_data.get(missing_slot):
            # Update the pending order memory
            pending_order.update(extracted_data)
            # Re-run validation to see if we have everything now
            return validate_and_execute_order(pending_order)
        else:
            return f"I didn't quite catch the {missing_slot}. Please say it again.", context

    # --- 2. NEW INTENT DETECTION ---
    intent = get_general_intent(text)
    print(f"[Logic]: Intent Detected -> {intent}")
    response_data = {"intent": intent}
    
    if intent == "MARKET_NEWS":
        topic_query = extract_news_topic(text)
        headlines = get_latest_market_news(topic_query)
        if headlines:
            summary = analyze_news_sentiment(headlines)
            spoken_topic = topic_query.replace(" Share Price India", "").replace("Indian Stock Market", "the market")
            response_text = f"Here is the latest news for {spoken_topic}. {summary}"
        else:
            response_text = f"I couldn't find any recent news for {topic_query}."

    elif intent == "GET_FUNDS":
        funds = dhan_api.get_funds()
        response_text = f"You have {funds:,.2f} rupees available." if funds is not None else "Unavailable."
        response_data["funds"] = funds

    elif intent == "GET_HOLDINGS":
        holdings_text = dhan_api.get_holdings_summary()
        response_text = holdings_text
        response_data["type"] = "HOLDINGS"

    elif intent == "GET_POSITIONS":
        positions_text = dhan_api.get_positions_summary()
        response_text = positions_text
        response_data["type"] = "POSITIONS"

    elif intent == "CHECK_PRICE":
        # Extract stock name from text
        # e.g., "What's the price of Reliance?"
        import re
        match = re.search(r"price of ([a-zA-Z\s]+)", text, re.IGNORECASE)
        stock_name = match.group(1).strip() if match else text
        
        # Use StockFinder to get security ID
        result = stock_finder.find_stock(stock_name)
        
        if result:
            price = dhan_api.get_live_price(result["security_id"])
            if price:
                response_text = f"{result['symbol']} is currently trading at {price:.2f} rupees."
                response_data.update({
                    "symbol": result["symbol"],
                    "price": price,
                    "security_id": result["security_id"]
                })
            else:
                response_text = f"I couldn't fetch the live price for {result['symbol']}."
        else:
            response_text = f"I couldn't find a stock matching '{stock_name}'."


    elif intent == "PLACE_ORDER":
        # First-time Order Parsing
        order_data = get_order_intent_gemini(text)
        
        if order_data and order_data.get("symbol"):
            # Resolve Symbol immediately
            id_results = stock_finder.find_security_id(order_data["symbol"])
            if id_results:
                sec_id, name = id_results[0]
                order_data["security_id"] = sec_id
                order_data["symbol_name"] = name
                order_data["exchange_segment"] = "NSE_EQ"
            else:
                return f"I couldn't find the stock {order_data['symbol']}.", {}
        
        # Send to Validator (Handles missing data by returning Context)
        return validate_and_execute_order(order_data)

    else:
        response_text = "I'm listening."

    return response_text, response_data

# --- API Endpoint ---
@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(request: UserRequest):
    user_text = request.message
    context = request.context
    
    # Process Logic
    reply_text, reply_data = process_command(user_text, context)
    
    # Generate Audio
    audio_bytes = generate_audio_bytes(reply_text)
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return BotResponse(
        text=reply_text,
        audio_base64=audio_b64,
        data=reply_data
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
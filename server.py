import asyncio
import json
import base64
import os
import re
import uvicorn
import websockets
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware 
from pydantic import BaseModel
from dotenv import load_dotenv

# Load environment variables FIRST
load_dotenv()

# --- SERVICES IMPORTS ---
from nlu_service import (
    get_general_intent, 
    get_order_intent_gemini, 
    analyze_news_sentiment,  
    fill_missing_slot_gemini, 
    extract_news_topic,
    gemini_model 
)
from speech_service import generate_audio_bytes
from dhan_handler import DhanHandler
from stock_finder import StockFinder
from news_service import get_latest_market_news
from chat_service import MarketChatEngine

# --- GLOBAL STATE ---
dhan_api = None
stock_finder = None
chat_engine = None
connected_clients = set() 

# --- INITIALIZATION LOGIC ---
try:
    dhan_api = DhanHandler(os.getenv("DHAN_CLIENT_ID"), os.getenv("DHAN_ACCESS_TOKEN"))
    stock_finder = StockFinder()
    chat_engine = MarketChatEngine(gemini_model, dhan_api)
    print("[Server]: Services initialized successfully.")
except Exception as e:
    print(f"[Server]: FATAL INIT ERROR: {e}")


# ==============================================================================
#  SECTION 1: REAL-TIME WEBSOCKETS & LIFESPAN
# ==============================================================================

async def dhan_socket_listener():
    """
    Connects to Dhan's Order Update WebSocket and forwards messages to our Frontend.
    """
    uri = "wss://api-order-update.dhan.co"
    
    while True:
        try:
            async with websockets.connect(uri) as ws:
                print("[WebSocket]: Connected to Dhan Order Stream")
                
                # 1. Authorize
                auth_payload = {
                    "LoginReq": {
                        "MsgCode": 42,
                        "ClientId": os.getenv("DHAN_CLIENT_ID"),
                        "Token": os.getenv("DHAN_ACCESS_TOKEN")
                    },
                    "UserType": "SELF"
                }
                await ws.send(json.dumps(auth_payload))
                
                # 2. Listen & Broadcast
                async for message in ws:
                    try:
                        data = json.loads(message)
                        
                        # DEBUG: Print raw message to see structure
                        # print(f"[WebSocket Raw]: {data}") 

                        if data.get("Type") == "order_alert":
                            order_info = data.get("Data", {})
                            
                            # Dhan keys are usually TitleCase (Symbol, Status, Price)
                            # We use .get() to be safe against missing keys
                            frontend_payload = {
                                "type": "ORDER_UPDATE",
                                "status": order_info.get("Status"),
                                "symbol": order_info.get("DisplayName") or order_info.get("Symbol"),
                                "price": order_info.get("Price"),
                                "text": f"Order for {order_info.get('DisplayName', 'Stock')} is now {order_info.get('Status')}."
                            }
                            
                            if connected_clients:
                                print(f"[WebSocket]: Broadcasting -> {frontend_payload}")
                                for client in connected_clients:
                                    await client.send_json(frontend_payload)
                    except Exception as parse_err:
                        print(f"[WebSocket Parse Error]: {parse_err}")

        except Exception as e:
            # Connection failed or dropped, retry in 5s
            await asyncio.sleep(5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    asyncio.create_task(dhan_socket_listener())
    yield
    # --- SHUTDOWN ---

# --- APP SETUP ---
app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- DATA MODELS ---
class UserRequest(BaseModel):
    message: str
    context: dict = {}

class BotResponse(BaseModel):
    text: str
    audio_base64: str
    data: dict = {}


# ==============================================================================
#  SECTION 2: TRADING LOGIC (Bulk, Max, Square Off, Super Order)
# ==============================================================================

def execute_square_off_all() -> str:
    """Closes all open positions via DhanHandler."""
    return dhan_api.square_off_all()

def calculate_dynamic_quantity(qty_str: str, action: str, price: float, funds: float) -> int:
    """
    Parses '50%', 'half', 'max', 'all' and returns integer quantity.
    Robust against sentences like "50% of my available margin".
    """
    qty_str = str(qty_str).lower().strip()
    
    # 1. Regex Extraction for Percentages (e.g. "50%", "25%")
    # Matches digits followed optionally by space then %
    percent_match = re.search(r"(\d+)\s*%", qty_str)
    
    ratio = 0.0
    
    if qty_str in ["max", "all", "full", "entire"]:
        ratio = 0.95 # 95% safety
    elif "half" in qty_str:
        ratio = 0.50
    elif "quarter" in qty_str:
        ratio = 0.25
    elif percent_match:
        try:
            percent = float(percent_match.group(1))
            ratio = percent / 100.0
        except:
            ratio = 0.0
            
    # 2. Calculate Quantity based on Action
    if ratio > 0:
        if action == "BUY":
            if funds <= 0 or price <= 0: return 0
            allocation = funds * ratio
            return int(allocation / price)
        elif action == "SELL":
            return -1 
            
    # 3. Fallback: Try to find a plain number in the string
    # e.g., "buy me 100 shares" -> 100
    try:
        # Extract first number found
        num_match = re.search(r"\b(\d+)\b", qty_str)
        if num_match:
            return int(num_match.group(1))
        return 0
    except:
        return 0

def validate_and_execute_order(order_data: dict) -> tuple[str, dict]:
    """Validates a SINGLE order. Handles 'MAX' & Percentage logic."""
    
    # 1. Check Symbol
    if not order_data.get("security_id"):
        return "Which stock do you want to trade?", {
            "status": "WAITING_FOR_SLOT", "missing_slot": "symbol", "pending_order": order_data
        }

    # 2. Check Action
    if not order_data.get("action"):
        return f"Do you want to Buy or Sell {order_data.get('symbol', 'the stock')}?", {
            "status": "WAITING_FOR_SLOT", "missing_slot": "action", "pending_order": order_data
        }

    # 3. Handle DYNAMIC Quantity (Max, 50%, Half)
    raw_qty = order_data.get("quantity")
    
    # Trigger logic if it's a string (e.g. "50%") OR "MAX"
    if raw_qty:
        # Check if we need to calculate
        is_dynamic = str(raw_qty).lower() in ["max", "all", "full"] or "%" in str(raw_qty) or "half" in str(raw_qty)
        
        if is_dynamic: 
            if order_data["action"].upper() == "BUY":
                funds = dhan_api.get_funds()
                price = order_data.get("price") or dhan_api.get_live_price(order_data["security_id"])
                
                if funds and price and price > 0:
                    calculated_qty = calculate_dynamic_quantity(str(raw_qty), "BUY", float(price), float(funds))
                    
                    if calculated_qty < 1:
                        return f"Insufficient funds to buy {raw_qty} of {order_data['symbol']} at {price}.", {}
                    
                    order_data["quantity"] = calculated_qty
                    print(f"[Logic]: Auto-calculated {raw_qty} -> {calculated_qty}")
                else:
                    return "I couldn't verify funds or price to calculate quantity.", {}
            else:
                 return "I can currently only calculate 'Max' or percentages for Buying.", {}

    # 4. Final Quantity Check
    if not order_data.get("quantity"):
        return f"How many shares of {order_data.get('symbol_name', 'it')}?", {
            "status": "WAITING_FOR_SLOT", "missing_slot": "quantity", "pending_order": order_data
        }
    
    # 5. SUPER ORDER CHECKS & PRICE FIX
    if order_data.get("is_super_order"):
        # Fix: Super Orders MUST have a price. If 0.0 (Market), fetch Live Price.
        if not order_data.get("price") or float(order_data.get("price")) == 0.0:
            live_price = dhan_api.get_live_price(order_data["security_id"])
            if live_price:
                order_data["price"] = float(live_price)
                print(f"[Logic]: Auto-filled Super Order Price to Live Price: {live_price}")
            else:
                return "I need a specific price for Super Orders (Target/Stop Loss cannot work with Market orders safely).", {}

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

    # 6. Execute
    result_text = dhan_api.place_voice_order(order_data)
    return result_text, {"intent": "ORDER_RESULT", "status": "COMPLETE"}

def handle_order_intent_logic(extracted_data: dict | list) -> tuple[str, dict]:
    """Router for Bulk, Square Off, or Single Orders."""
    
    # Case A: Square Off All
    if isinstance(extracted_data, dict) and extracted_data.get("action") == "SQUARE_OFF_ALL":
        result = execute_square_off_all()
        return result, {"intent": "ORDER_RESULT"}

    # Case B: Bulk Orders (List)
    if isinstance(extracted_data, dict) and "orders" in extracted_data:
        orders_list = extracted_data["orders"]
        results = []
        for order in orders_list:
            if order.get("symbol"):
                id_res = stock_finder.find_security_id(order["symbol"])
                if id_res:
                    order["security_id"], order["symbol_name"] = id_res[0]
                    order["exchange_segment"] = "NSE_EQ"
            
            if order.get("security_id") and order.get("action"):
                # Handle MAX logic for bulk items briefly
                raw_qty = str(order.get("quantity")).lower()
                if raw_qty in ["max", "all"] and order["action"].upper() == "BUY":
                     funds = dhan_api.get_funds()
                     price = dhan_api.get_live_price(order["security_id"])
                     if funds and price: order["quantity"] = int((funds * 0.95) / price)
                
                if not order.get("quantity"):
                    results.append(f"{order.get('symbol', 'Stock')}: Missing quantity.")
                    continue

                res_text = dhan_api.place_voice_order(order)
                results.append(f"{order['symbol']}: {res_text}")
            else:
                results.append(f"{order.get('symbol', 'Unknown')}: Invalid details.")
        
        return "Bulk Order Summary: " + " | ".join(results), {"intent": "ORDER_RESULT"}

    # Case C: Single Order
    order_data = extracted_data
    if order_data and order_data.get("symbol") and not order_data.get("security_id"):
        id_results = stock_finder.find_security_id(order_data["symbol"])
        if id_results:
            sec_id, name = id_results[0]
            order_data["security_id"] = sec_id
            order_data["symbol_name"] = name
            order_data["exchange_segment"] = "NSE_EQ"
        else:
            return f"I couldn't find the stock {order_data['symbol']}.", {}

    return validate_and_execute_order(order_data)


# ==============================================================================
#  SECTION 3: MAIN COMMAND ROUTER
# ==============================================================================

def extract_stock_for_margin(text: str) -> dict | None:
    """
    Uses Gemini to extract Symbol and Qty specifically for Check Margin intent.
    Helps avoid the 'Search for every word' issue.
    """
    prompt = f"""
    Extract STOCK SYMBOL and QUANTITY from this margin query.
    Default quantity to 1 if not specified.
    
    User Query: "{text}"
    
    Output JSON: {{ "symbol": "string", "quantity": int }}
    """
    try:
        response = gemini_model.generate_content(prompt)
        text = response.text.strip().replace("```json", "").replace("```", "")
        return json.loads(text)
    except:
        return None

def process_command(text: str, context: dict) -> tuple[str, dict]:
    
    # 1. Slot Filling
    if context and context.get("status") == "WAITING_FOR_SLOT":
        pending_order = context.get("pending_order", {})
        missing_slot = context.get("missing_slot")
        
        print(f"[Logic]: User answered slot '{missing_slot}' with: '{text}'")
        extracted_data = fill_missing_slot_gemini(pending_order, text, missing_slot)
        
        if extracted_data:
            pending_order.update(extracted_data)
            return validate_and_execute_order(pending_order)
        else:
            return f"I didn't quite catch the {missing_slot}. Please say it again.", context

    # 2. Intent Detection
    intent = get_general_intent(text)
    print(f"[Logic]: Intent Detected -> {intent}")
    response_data = {"intent": intent}
    
    # --- HANDLERS ---
    
    if intent == "MARKET_NEWS":
        topic_query = extract_news_topic(text)
        headlines = get_latest_market_news(topic_query)
        if headlines:
            summary = analyze_news_sentiment(headlines)
            spoken_topic = topic_query.replace(" Share Price India", "").replace("Indian Stock Market", "the market")
            response_text = f"Latest news for {spoken_topic}: {summary}"
        else:
            response_text = f"No recent news found for {topic_query}."

    elif intent == "GET_FUNDS":
        funds = dhan_api.get_funds()
        response_text = f"Available balance: {funds:,.2f} rupees." if funds is not None else "Cannot fetch funds."
        response_data["funds"] = funds

    elif intent == "GET_HOLDINGS":
        response_text = dhan_api.get_holdings_summary()
        response_data["type"] = "HOLDINGS"

    elif intent == "GET_POSITIONS":
        response_text = dhan_api.get_positions_summary()
        response_data["type"] = "POSITIONS"

    elif intent == "GET_ORDERS":
        response_text = dhan_api.get_pending_orders()
        response_data["type"] = "TEXT" 

    elif intent == "CHECK_MARGIN":
        # New Smart Extraction Logic
        margin_data = extract_stock_for_margin(text)
        
        if margin_data and margin_data.get("symbol"):
            # Use StockFinder to get ID
            res = stock_finder.find_security_id(margin_data["symbol"])
            if res:
                sec_id, name = res[0]
                qty = margin_data.get("quantity", 1)
                margin = dhan_api.get_margin_requirement(sec_id, qty)
                
                response_text = f"Required margin for {qty} shares of {name} is approx {margin} rupees." if margin else "Could not calculate margin."
            else:
                response_text = f"I couldn't find the stock {margin_data['symbol']}."
        else:
            response_text = "Which stock do you want to check margin for?"

    elif intent == "CHECK_PRICE":
        import re
        match = re.search(r"price of ([a-zA-Z\s]+)", text, re.IGNORECASE)
        stock_name = match.group(1).strip() if match else text
        
        result = stock_finder.find_stock(stock_name)
        if result:
            price = dhan_api.get_live_price(result["security_id"])
            if price:
                response_text = f"{result['symbol']} is at {price:.2f}."
                response_data.update({"symbol": result["symbol"], "price": price, "security_id": result["security_id"]})
            else:
                response_text = f"Could not fetch price for {result['symbol']}."
        else:
            response_text = f"Stock '{stock_name}' not found."

    elif intent == "PLACE_ORDER":
        order_intent_data = get_order_intent_gemini(text)
        return handle_order_intent_logic(order_intent_data)

    # 3. Fallback to CHAT
    else:
        if chat_engine:
            response_text = chat_engine.generate_reply(text)
            response_data["type"] = "CHAT"
            response_data["intent"] = "CONVERSATIONAL" 
        else:
            response_text = "I'm listening, but my chat engine is offline."

    return response_text, response_data

# --- API ENDPOINTS ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        connected_clients.remove(websocket)

@app.post("/chat", response_model=BotResponse)
async def chat_endpoint(request: UserRequest):
    print(f"\n[User Spoke]: \"{request.message}\"")
    
    reply_text, reply_data = process_command(request.message, request.context)
    
    audio_bytes = generate_audio_bytes(reply_text)
    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    
    return BotResponse(text=reply_text, audio_base64=audio_b64, data=reply_data)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
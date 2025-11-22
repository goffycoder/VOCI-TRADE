# --- Standard Imports ---
import pvporcupine
import pyaudio
import struct
import json
import os
import time
from dotenv import load_dotenv
import getpass  
import re   
import sys
    
# --- 1. Load All Keys and Initialize# Load env vars
print("Loading environment variables from .env...")
load_dotenv()
print("Environment variables loaded.")

print(f"Python Executable: {sys.executable}")

print("Importing DhanHandler...")
from dhan_handler import DhanHandler
print("Importing StockFinder...")
from stock_finder import StockFinder
print("Importing Speech Service...")
from speech_service import say_text, record_audio, transcribe_audio
print("Importing NLU Service...")
from nlu_service import get_order_intent_gemini, fill_missing_slot_gemini
print("Importing OrderUpdateListener...")
from order_updater import OrderUpdateListener
print("Importing MockDhanHandler...")
from simulation_handler import MockDhanHandler
print("Imports complete.")


# Picovoice
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
if not PICOVOICE_ACCESS_KEY:
    print("FATAL ERROR: PICOVOICE_ACCESS_KEY not found in .env file.")
    exit()

# Dhan
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
dhan_api = DhanHandler(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

# Stock Finder
try:
    stock_finder = StockFinder() 
except Exception as e:
    print(f"FATAL ERROR: Could not initialize StockFinder: {e}")
    exit()

# --- 2. Constants and State ---
SAMPLE_RATE = 16000
FRAME_LENGTH = 512
TEMP_WAV_FILE = "temp_command.wav"
COMMAND_DURATION_SEC = 7
ANSWER_DURATION_SEC = 4 

# --- Security PINs ---
STARTUP_PIN = "252604"
CONFIRM_PIN = "9090"

# --- Define our (full) application states ---
STATE_LISTENING_FOR_WAKE_WORD = "LISTENING_FOR_WAKE_WORD"
STATE_RECORDING_COMMAND = "RECORDING_COMMAND"
STATE_PROCESSING = "PROCESSING"
STATE_AWAITING_ANSWER = "AWAITING_ANSWER" 
STATE_RECORDING_ANSWER = "RECORDING_ANSWER" 

# --- 3. Helper Functions ---
def get_keyboard_input(prompt: str) -> str:
    """Waits for and returns user input from the keyboard."""
    print(f"[Ledger]: {prompt}")
    user_input = input("Your input: ")
    return user_input.strip()

# --- 4. Main Application ---
def main():
    porcupine = None
    audio_stream = None
    pa = pyaudio.PyAudio()
    
    is_authenticated = False 
    current_state = STATE_LISTENING_FOR_WAKE_WORD
    pending_order = {} 
    missing_slot = None  

    try:
        # --- Initialization ---
        KEYWORD_PATH = "/Users/vrajpatel/Downloads/Hey-Ledger_en_mac_v3_0_0/Hey-Ledger_en_mac_v3_0_0.ppn"
        porcupine = pvporcupine.create(access_key=PICOVOICE_ACCESS_KEY, keyword_paths=[KEYWORD_PATH], sensitivities=[0.7])
        print("[Picovoice]: Wake word engine initialized.")
        
        audio_stream = pa.open(rate=SAMPLE_RATE, channels=1, format=pyaudio.paInt16, input=True, frames_per_buffer=FRAME_LENGTH)
        print("[PyAudio]: Audio stream initialized.")
        
        print("\nInitialization complete.")
        # --- SIMULATION MODE TOGGLE ---
        # Set to True to use Mock Handler (no real funds/trades)
        SIMULATION_MODE = True 
        
        if SIMULATION_MODE:
            print("\n[Ledger]: STARTING IN SIMULATION MODE.")
            say_text("Starting in Simulation Mode.")
            dhan_api = MockDhanHandler(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
        else:
            print("\n[Ledger]: STARTING IN REAL TRADING MODE.")
            dhan_api = DhanHandler(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
            
        stock_finder = StockFinder()
        
        # Only check market status if NOT in simulation mode (or mock it too)
        if not SIMULATION_MODE:
            market_status = dhan_api.check_market_status()
            if not market_status:
                say_text("Warning: Market is currently closed.")
        else:
            print("[Ledger]: Skipping market status check (Simulation).")

        say_text("Ledger is online.")

        # --- Start Order Update Listener (Phase 5) ---
        try:
            order_listener = OrderUpdateListener(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)
            order_listener.start()
        except Exception as e:
            print(f"Warning: Could not start Order Update Listener: {e}")

        # --- Startup PIN check using keyboard ---
        while not is_authenticated:
            print("[Ledger]: Please provide the 6-digit startup code in the terminal:")
            pin_attempt = getpass.getpass("Enter 6-digit PIN: ")
            
            if pin_attempt == STARTUP_PIN:
                is_authenticated = True
                say_text("Startup code accepted. Ledger is ready.")
            else:
                print("[Ledger]: Incorrect code. Please try again.")

        # --- THE STATE MACHINE LOOP ---
        while True:
            
            if current_state == STATE_LISTENING_FOR_WAKE_WORD:
                print(f"\n[{current_state}] Listening for 'Hey Ledger'...")
                pcm_bytes = audio_stream.read(FRAME_LENGTH, exception_on_overflow=False)
                pcm_unpacked = struct.unpack_from("h" * FRAME_LENGTH, pcm_bytes)
                
                if porcupine.process(pcm_unpacked) >= 0:
                    print(">>> Wake word detected! <<<")
                    say_text("I'm listening.")
                    current_state = STATE_RECORDING_COMMAND

            elif current_state == STATE_RECORDING_COMMAND:
                record_audio(COMMAND_DURATION_SEC, TEMP_WAV_FILE, audio_stream, FRAME_LENGTH, SAMPLE_RATE)
                current_state = STATE_PROCESSING
            
            elif current_state == STATE_RECORDING_ANSWER:
                # --- THIS IS THE NameError FIX ---
                record_audio(ANSWER_DURATION_SEC, TEMP_WAV_FILE, audio_stream, FRAME_LENGTH, SAMPLE_RATE)
                current_state = STATE_PROCESSING 
            
            elif current_state == STATE_PROCESSING:
                
                if missing_slot:
                    # --- We are processing an ANSWER ---
                    voice_failed = False
                    transcription = transcribe_audio(TEMP_WAV_FILE, SAMPLE_RATE)
                    
                    if not transcription:
                        voice_failed = True
                        say_text("I didn't catch that. Please use your keyboard.")
                    
                    if not voice_failed:
                        # --- 1. Try voice for stock disambiguation ---
                        if missing_slot == "symbol_disambiguation":
                            print(f"[Disambiguation]: User answered '{transcription}'")
                            options = pending_order.get("options", [])
                            best_match = None
                            search_term = transcription.lower()
                            
                            # --- IndexError FIX: Tuple now has 2 parts ---
                            for (security_id, full_name) in options:
                                if search_term in full_name.lower():
                                    best_match = (security_id, full_name)
                                    break 
                            
                            if best_match:
                                print(f"[Disambiguation]: Matched to '{best_match[1]}'")
                                pending_order["security_id"] = best_match[0]
                                pending_order["symbol_name"] = best_match[1]
                                del pending_order["options"] 
                                missing_slot = None # Success!
                            else:
                                voice_failed = True
                                say_text(f"I didn't understand '{transcription}'. Please use your keyboard.")
                        
                        # --- 2. Try voice for normal slot-filling ---
                        else: 
                            extracted_data = fill_missing_slot_gemini(pending_order, transcription, missing_slot)
                            if extracted_data and extracted_data.get(missing_slot): # Check for key presence
                                pending_order.update(extracted_data)
                                missing_slot = None # Success!
                            else:
                                voice_failed = True
                                say_text("I still didn't get that. Please use your keyboard.")
                    
                    # --- 3. KEYBOARD FALLBACK ---
                    if voice_failed:
                        if missing_slot == "symbol_disambiguation":
                            options = pending_order.get("options", [])
                            print("\n--- Multiple Stock Matches ---")
                            # --- IndexError FIX: Tuple now has 2 parts ---
                            for i, (sec_id, name) in enumerate(options):
                                print(f"  {i+1}: {name}") 
                            print("--------------------------------")
                            
                            choice_str = get_keyboard_input(f"Enter the number (1-{len(options)}) for the stock you want:")
                            try:
                                choice_idx = int(choice_str) - 1
                                if 0 <= choice_idx < len(options):
                                    id_result = options[choice_idx]
                                    pending_order["security_id"] = id_result[0]
                                    pending_order["symbol_name"] = id_result[1]
                                    del pending_order["options"]
                                    missing_slot = None # Success!
                                else:
                                    raise ValueError("Choice out of range")
                            except Exception as e:
                                print(f"Error: {e}")
                                say_text("That's not a valid selection. Cancelling order.")
                                current_state = STATE_LISTENING_FOR_WAKE_WORD
                                pending_order = {}
                                missing_slot = None
                                continue 
                        
                        elif missing_slot == "action":
                            choice = get_keyboard_input("Enter 1 for BUY or 2 for SELL:")
                            if choice == "1":
                                pending_order["action"] = "BUY"
                                missing_slot = None 
                            elif choice == "2":
                                pending_order["action"] = "SELL"
                                missing_slot = None 
                            else:
                                say_text("Invalid choice. Cancelling order.")
                                current_state = STATE_LISTENING_FOR_WAKE_WORD
                                pending_order = {} 
                                missing_slot = None
                                continue

                        elif missing_slot == "quantity":
                            choice = get_keyboard_input("Enter quantity:")
                            try:
                                pending_order["quantity"] = int(choice)
                                missing_slot = None 
                            except ValueError:
                                say_text("That's not a valid number. Cancelling order.")
                                current_state = STATE_LISTENING_FOR_WAKE_WORD
                                pending_order = {} 
                                missing_slot = None
                                continue
                        
                        elif missing_slot == "symbol":
                            choice = get_keyboard_input("Enter stock name:")
                            pending_order["symbol"] = choice
                            missing_slot = None 

                else:
                    # --- We are processing a NEW COMMAND ---
                    transcription = transcribe_audio(TEMP_WAV_FILE, SAMPLE_RATE)
                    if not transcription:
                        say_text("I didn't catch that. Please try again.")
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        continue
                        
                    pending_order = get_order_intent_gemini(transcription)
                    if not pending_order:
                        say_text("Sorry, I had trouble understanding the command.")
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        continue

                    # --- NEW: Handle Portfolio Intent ---
                    if pending_order.get("intent") == "GET_PORTFOLIO":
                        print("[Ledger]: Processing Portfolio Query...")
                        say_text("Fetching your portfolio details...")
                        
                        holdings = dhan_api.get_holdings()
                        positions = dhan_api.get_positions()
                        
                        summary_parts = []
                        
                        # Process Holdings
                        if holdings:
                            holding_count = len(holdings)
                            summary_parts.append(f"You have {holding_count} stocks in your long-term holdings.")
                            # Optional: List top 3 or specific details if needed
                        else:
                            summary_parts.append("You have no long-term holdings.")

                        # Process Positions
                        if positions:
                            open_positions = [p for p in positions if p.get('positionType') != 'CLOSED']
                            if open_positions:
                                pos_count = len(open_positions)
                                summary_parts.append(f"You have {pos_count} open intraday positions.")
                            else:
                                summary_parts.append("You have no open intraday positions.")
                        else:
                            summary_parts.append("You have no open positions.")
                        
                        full_summary = " ".join(summary_parts)
                        say_text(full_summary)
                        
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        pending_order = {}
                        continue

                    # --- NEW: Handle Price Intent ---
                    if pending_order.get("intent") == "GET_PRICE":
                        symbol = pending_order.get("symbol")
                        if not symbol:
                            say_text("Which stock price do you want to know?")
                            # For simplicity in this phase, we just reset. 
                            # Ideally we'd enter a slot filling loop, but let's keep it simple.
                            current_state = STATE_LISTENING_FOR_WAKE_WORD
                            continue

                        print(f"[Ledger]: Fetching price for '{symbol}'...")
                        
                        # Resolve symbol to ID
                        id_results = stock_finder.find_security_id(symbol)
                        
                        if not id_results:
                            say_text(f"Sorry, I couldn't find a stock matching {symbol}.")
                        elif len(id_results) > 1:
                            # For price check, just pick the first best match to be quick
                            # or ask for clarification. Let's pick first for speed.
                            best_match = id_results[0]
                            sec_id = best_match[0]
                            name = best_match[1]
                            
                            price = dhan_api.fetch_ltp(sec_id)
                            if price:
                                say_text(f"The current price of {name} is {price} rupees.")
                            else:
                                say_text(f"Sorry, I couldn't fetch the price for {name}.")
                        else:
                            # Exact match
                            sec_id = id_results[0][0]
                            name = id_results[0][1]
                            price = dhan_api.fetch_ltp(sec_id)
                            if price:
                                say_text(f"The current price of {name} is {price} rupees.")
                            else:
                                say_text(f"Sorry, I couldn't fetch the price for {name}.")
                        
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        pending_order = {}
                        continue

                    # --- NEW: Handle Convert Position ---
                    if pending_order.get("intent") == "CONVERT_POSITION":
                        symbol = pending_order.get("symbol")
                        quantity = pending_order.get("quantity")
                        
                        if not symbol or not quantity:
                            say_text("I need the stock name and quantity to convert.")
                            current_state = STATE_LISTENING_FOR_WAKE_WORD
                            continue
                        
                        # Resolve symbol
                        id_results = stock_finder.find_security_id(symbol)
                        if not id_results:
                            say_text(f"Stock {symbol} not found.")
                            current_state = STATE_LISTENING_FOR_WAKE_WORD
                            continue
                        
                        # Assume first match
                        sec_id = id_results[0][0]
                        
                        # We need 'action' (BUY/SELL) to know which position to convert.
                        # Since NLU might not extract 'action' for convert intent (it's implicit in the position),
                        # we might need to ask or fetch positions to see what we have.
                        # For simplicity Phase 4: We assume user has a BUY position they want to convert.
                        # Or we can fetch positions and check.
                        
                        # Let's try to be smart: Fetch positions, find the one for this symbol, get its type.
                        positions = dhan_api.get_positions()
                        target_pos = None
                        if positions:
                            for p in positions:
                                if p['securityId'] == sec_id and p['positionType'] != 'CLOSED':
                                    target_pos = p
                                    break
                        
                        if not target_pos:
                            say_text(f"You don't have any open positions in {symbol}.")
                            current_state = STATE_LISTENING_FOR_WAKE_WORD
                            continue
                        
                        # Construct order details for conversion
                        convert_details = {
                            "security_id": sec_id,
                            "exchange_segment": target_pos['exchangeSegment'],
                            "quantity": quantity,
                            "action": target_pos['positionType'] # BUY or SELL
                        }
                        
                        say_text(f"Converting {quantity} shares of {symbol}. Please confirm with your PIN.")
                        pin_attempt = getpass.getpass("Enter 4-digit PIN: ")
                        if pin_attempt == CONFIRM_PIN:
                            result = dhan_api.convert_position(convert_details)
                            say_text(result)
                        else:
                            say_text("Incorrect PIN. Conversion cancelled.")
                            
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        pending_order = {}
                        continue

                    # --- NEW: Handle Kill Switch ---
                    if pending_order.get("intent") == "KILL_SWITCH":
                        say_text("WARNING. You have requested to close ALL positions. This is irreversible. Are you sure?")
                        # We could listen for "YES", but for safety, let's use the PIN or a specific keyboard input.
                        print("\n[KILL SWITCH]: Type 'CONFIRM' to square off all positions.")
                        confirm_input = input("Type 'CONFIRM': ")
                        
                        if confirm_input == "CONFIRM":
                            say_text("Executing Kill Switch.")
                            result = dhan_api.square_off_all()
                            say_text(result)
                        else:
                            say_text("Kill switch cancelled.")
                            
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        pending_order = {}
                        continue
                    
                    # --- Default to Order Flow ---
                    # If intent is ORDER or missing (backward compatibility), proceed.


                # --- Slot Checking & Follow-up ---
                if not pending_order.get("action"):
                    say_text("Should I buy or sell?")
                    current_state = STATE_AWAITING_ANSWER
                    missing_slot = "action"
                    continue
                
                if not pending_order.get("quantity"):
                    say_text("How many shares?")
                    current_state = STATE_AWAITING_ANSWER
                    missing_slot = "quantity"
                    continue
                
                if not pending_order.get("symbol"):
                    say_text("Which stock?")
                    current_state = STATE_AWAITING_ANSWER
                    missing_slot = "symbol"
                    continue
                
                # --- IndexError FIX: Check for security_id (no exchange) ---
                if "security_id" not in pending_order:
                    # id_results is now list[(id, name)]
                    id_results = stock_finder.find_security_id(pending_order["symbol"])
                    
                    if len(id_results) == 0:
                        say_text(f"Sorry, I couldn't find a stock matching {pending_order['symbol']}. Which stock did you mean?")
                        current_state = STATE_AWAITING_ANSWER
                        missing_slot = "symbol"
                        pending_order["symbol"] = None 
                        continue

                    elif len(id_results) == 1:
                        id_result = id_results[0]
                        pending_order["security_id"] = id_result[0]
                        pending_order["symbol_name"] = id_result[1]
                        pending_order["exchange_segment"] = "NSE_EQ" # <-- HARDCODE "NSE_EQ"
                        print(f"[StockFinder]: Matched to {id_result[1]} on NSE_EQ")

                    else:
                        pending_order["options"] = id_results
                        option_names = []
                        # --- IndexError FIX: Tuple has 2 parts ---
                        for (id, name) in id_results:
                            short_name = " ".join(name.split()[:3])
                            option_names.append(short_name)

                        say_text(f"Which {pending_order['symbol']} did you mean?")
                        time.sleep(0.5) 
                        
                        for name in option_names:
                            say_text(name)
                            time.sleep(0.7) 
                        
                        current_state = STATE_AWAITING_ANSWER
                        missing_slot = "symbol_disambiguation"
                        continue

                # --- Pre-Trade Intelligence: Fund & Margin Check ---
                print("[Ledger]: Checking funds and margin...")
                available_funds = dhan_api.get_fund_limit()
                
                # Calculate margin (assuming Market order uses approx price or 0 if not available, 
                # but margin calc usually needs a price. For market orders, we might need to fetch LTP first 
                # or let the API handle it if it supports 0 price for market orders. 
                # Based on previous code, we use 0.0 for market orders. 
                # If margin calc fails with 0, we might skip this check or use a dummy price.)
                # For now, we pass the price from pending_order which is 0.0 for MARKET.
                required_margin = dhan_api.get_order_margin(
                    security_id=pending_order["security_id"],
                    quantity=pending_order["quantity"],
                    transaction_type=pending_order["action"],
                    product_type="INTRADAY",
                    price=float(pending_order.get("price", 0.0))
                )

                if available_funds is not None and required_margin is not None:
                    print(f"[Ledger]: Funds: {available_funds}, Margin Needed: {required_margin}")
                    
                    if available_funds < required_margin:
                        shortfall = required_margin - available_funds
                        say_text(f"Insufficient funds. You have {available_funds:.2f} rupees, but this trade requires {required_margin:.2f} rupees. You are short by {shortfall:.2f} rupees. Order cancelled.")
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        pending_order = {}
                        missing_slot = None
                        continue
                    else:
                        say_text(f"Margin required is {required_margin:.2f} rupees. You have sufficient funds.")
                else:
                    print("[Ledger]: Could not verify funds/margin. Proceeding with caution.")
                    # Optional: Warn the user that check failed? For now, we proceed silently to not block trading.

                # --- FINAL STEP: Request Confirmation PIN via Keyboard ---
                say_text(f"Just to confirm, you want to {pending_order['action']} {pending_order['quantity']} shares of {pending_order['symbol_name']}.")
                time.sleep(1.0) 
                
                print(f"\n[Ledger]: Please provide the 4-digit confirmation code in the terminal to execute the trade:")
                pin_attempt = getpass.getpass("Enter 4-digit PIN: ")
                
                if pin_attempt == CONFIRM_PIN:
                    say_text("Code accepted. Placing your order...")
                    response_message = dhan_api.place_voice_order(pending_order)
                    say_text(response_message)
                else:
                    say_text("Incorrect confirmation code. Order cancelled.")
                
                current_state = STATE_LISTENING_FOR_WAKE_WORD
                pending_order = {}
                missing_slot = None
                continue 

            elif current_state == STATE_AWAITING_ANSWER:
                print(f"[{current_state}] Listening for answer for '{missing_slot}'...")
                current_state = STATE_RECORDING_ANSWER

            time.sleep(0.01) # Prevent high CPU usage

    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if porcupine: porcupine.delete()
        if audio_stream:
            audio_stream.stop_stream()
            audio_stream.close()
        if pa: pa.terminate()
        if os.path.exists(TEMP_WAV_FILE):
            os.remove(TEMP_WAV_FILE)
        print("Cleanup complete. Exiting.")

if __name__ == "__main__":
    main()

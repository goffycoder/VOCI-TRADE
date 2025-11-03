# --- Standard Imports ---
import pvporcupine
import pyaudio
import struct
import json
import os
import wave
import time
from dotenv import load_dotenv
import getpass  # For secure password input
import re       # For cleaning strings

# --- Cloud & Local Tool Imports ---
import google.generativeai as genai
from google.cloud import speech
from elevenlabs import ElevenLabs

# --- Your Project Modules ---
from dhan_handler import DhanHandler
from stock_finder import StockFinder

# --- 1. Load All Keys and Initialize Clients ---
print("Loading environment variables from .env...")
load_dotenv()

# Picovoice
PICOVOICE_ACCESS_KEY = os.getenv("PICOVOICE_ACCESS_KEY")
if not PICOVOICE_ACCESS_KEY:
    print("FATAL ERROR: PICOVOICE_ACCESS_KEY not found in .env file.")
    exit()

# Dhan
DHAN_CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
DHAN_ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")
if not DHAN_CLIENT_ID or not DHAN_ACCESS_TOKEN:
    print("FATAL ERROR: Dhan keys not found in .env file.")
    exit()
dhan_api = DhanHandler(DHAN_CLIENT_ID, DHAN_ACCESS_TOKEN)

# Google AI (Gemini)
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    print("FATAL ERROR: GOOGLE_API_KEY not found in .env file.")
    exit()
genai.configure(api_key=GOOGLE_API_KEY)
gemini_model = genai.GenerativeModel('models/gemini-flash-latest') # Use the model you found

# Google Speech-to-Text
try:
    speech_client = speech.SpeechClient()
    print("[Google STT]: Client initialized.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize Google Speech Client: {e}")
    print("Please ensure 'GOOGLE_APPLICATION_CREDENTIALS' is set correctly.")
    exit()

# ElevenLabs TTS
ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
if not ELEVENLABS_API_KEY:
    print("FATAL ERROR: ELEVENLABS_API_KEY not found in .env file.")
    exit()
eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
print("[ElevenLabs]: Client initialized.")

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
ANSWER_DURATION_SEC = 4 # We need this again

# --- Security PINs ---
STARTUP_PIN = "252604"
CONFIRM_PIN = "9090"

# --- Define our (full) application states ---
STATE_LISTENING_FOR_WAKE_WORD = "LISTENING_FOR_WAKE_WORD"
STATE_RECORDING_COMMAND = "RECORDING_COMMAND"
STATE_PROCESSING = "PROCESSING"
STATE_AWAITING_ANSWER = "AWAITING_ANSWER" # It's back
STATE_RECORDING_ANSWER = "RECORDING_ANSWER" # It's back


# --- 3. Helper Functions ---
def say_text(text: str):
    """Speaks text using ElevenLabs API."""
    print(f"[Ledger]: {text}")
    try:
        from elevenlabs import stream
        audio_stream = eleven_client.text_to_speech.convert(
            text=text,
            voice_id="21m00Tcm4TlvDq8ikWAM",
            model_id="eleven_multilingual_v2",
            output_format="mp3_44100_128"
        )
        stream(audio_stream)
    except Exception as e:
        print(f"ElevenLabs TTS Error: {e}")

def record_audio(duration_sec, file_path, audio_stream):
    """Records audio from the stream for a set duration and saves to file."""
    print(f"Recording for {duration_sec} seconds...")
    frames = []
    num_frames = int((SAMPLE_RATE / FRAME_LENGTH) * duration_sec)
    for _ in range(num_frames):
        try:
            data = audio_stream.read(FRAME_LENGTH, exception_on_overflow=False)
            frames.append(data)
        except IOError:
            pass 
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
    wf.setframerate(SAMPLE_RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"Audio saved to {file_path}")

def transcribe_audio(file_path: str) -> str:
    """Sends a local audio file to Google Cloud Speech-to-Text."""
    print(f"Sending {file_path} to Google STT...")
    try:
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=SAMPLE_RATE,
            language_code="en-IN",
        )
        response = speech_client.recognize(config=config, audio=audio)
        if response.results:
            transcription = response.results[0].alternatives[0].transcript
            print(f"Google STT Result: '{transcription}'")
            return transcription
        return ""
    except Exception as e:
        print(f"Google STT Error: {e}")
        return ""

def get_order_intent_gemini(transcription: str) -> dict | None:
    """Uses Gemini to parse the initial command."""
    prompt = f"""
    You are an NLU system for a stock trading app. Analyze the user's command
    and extract the details into a JSON object.
    
    The JSON must have: "action", "quantity", "symbol", "price", "order_type".
    
    - "action": "BUY" or "SELL".
    - "quantity": An integer.
    - "symbol": The spoken name of the stock (e.g., "reliance", "amara raja").
    - "price": A float. If no price is mentioned, set to 0.0.
    - "order_type": "MARKET" or "LIMIT". If a price is mentioned, it's "LIMIT".
    
    IMPORTANT: If any value is missing, set it to null. DO NOT GUESS.
    
    User Command: "{transcription}"
    
    JSON Output:
    """
    print("Sending text to Gemini for initial NLU...")
    response = None 
    try:
        response = gemini_model.generate_content(prompt)
        json_string = response.text.strip().lstrip("```json").rstrip("```").strip()
        print(f"Gemini NLU Result: {json_string}")
        return json.loads(json_string)
    except Exception as e:
        response_text = response.text if response else "No response"
        print(f"Gemini NLU Error: {e} | Response was: {response_text}")
        return None

# We need this function again
def fill_missing_slot_gemini(pending_order: dict, follow_up_answer: str, missing_slot: str) -> dict | None:
    """Uses Gemini to fill a single missing piece of information."""
    prompt = f"""
    You are an NLU system. The user's initial command was to:
    {json.dumps(pending_order, indent=2)}
    
    We were missing the "{missing_slot}". We asked them for it.
    The user's new answer is: "{follow_up_answer}"
    
    Analyze the user's answer and extract the single missing value.
    If the answer is "buy" or "sell", extract the action.
    If the answer is a quantity, extract the integer.
    If the answer is a price, extract the float.
    
    Example:
    Answer: "buy" -> "BUY"
    Answer: "five shares" -> 5
    Answer: "at one thousand" -> 1000.0
    
    Return a JSON object with *only* the new value for the missing slot.
    {{
      "{missing_slot}": "YOUR_EXTRACTED_VALUE_HERE"
    }}
    
    JSON Output:
    """
    print(f"Sending text to Gemini to fill slot: '{missing_slot}'")
    response = None 
    try:
        response = gemini_model.generate_content(prompt)
        json_string = response.text.strip().lstrip("```json").rstrip("```").strip()
        print(f"Gemini Slot-Fill Result: {json_string}")
        return json.loads(json_string)
    except Exception as e:
        response_text = response.text if response else "No response"
        print(f"Gemini Slot-Fill Error: {e} | Response was: {response_text}")
        return None

# Helper for keyboard input
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
        
        print("\nInitialization complete. Using Cloud-Powered NLU.")
        say_text("Ledger is online.")

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
                record_audio(COMMAND_DURATION_SEC, TEMP_WAV_FILE, audio_stream)
                current_state = STATE_PROCESSING
            
            elif current_state == STATE_RECORDING_ANSWER:
                record_audio(ANSWER_DURATION_SEC, TEMP_WAV_FILE, audio_stream)
                current_state = STATE_PROCESSING 
            
            elif current_state == STATE_PROCESSING:
                
                # --- This is the core conversational logic ---
                
                # If 'missing_slot' is set, we are processing an *answer*.
                # If 'missing_slot' is None, we are processing a *new command*.
                
                if missing_slot:
                    # --- We are processing an ANSWER ---
                    
                    voice_failed = False
                    transcription = transcribe_audio(TEMP_WAV_FILE)
                    
                    if not transcription:
                        voice_failed = True
                        say_text("I didn't catch that. Please use your keyboard.")
                    
                    # --- HYBRID LOGIC BLOCK ---
                    
                    if not voice_failed:
                        
                        # --- 1. Try voice for stock disambiguation ---
                        if missing_slot == "symbol_disambiguation":
                            print(f"[Disambiguation]: User answered '{transcription}'")
                            options = pending_order.get("options", [])
                            best_match = None
                            search_term = transcription.lower()
                            
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
                            if extracted_data and extracted_data.get(missing_slot):
                                pending_order.update(extracted_data)
                                missing_slot = None # Success!
                            else:
                                voice_failed = True
                                say_text("I still didn't get that. Please use your keyboard.")
                    

                    # --- 3. KEYBOARD FALLBACK ---
                    # If voice_failed is true, we now ask via keyboard.
                    if voice_failed:
                        
                        # --- Keyboard Fallback for Stock Disambiguation ---
                        if missing_slot == "symbol_disambiguation":
                            options = pending_order.get("options", [])
                            print("\n--- Multiple Stock Matches ---")
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
                                pending_order = {} # Reset
                                missing_slot = None
                                continue # Reset the whole loop
                        
                        # --- Keyboard Fallback for ACTION ---
                        elif missing_slot == "action":
                            choice = get_keyboard_input("Enter 1 for BUY or 2 for SELL:")
                            if choice == "1":
                                pending_order["action"] = "BUY"
                                missing_slot = None # Success!
                            elif choice == "2":
                                pending_order["action"] = "SELL"
                                missing_slot = None # Success!
                            else:
                                say_text("Invalid choice. Cancelling order.")
                                current_state = STATE_LISTENING_FOR_WAKE_WORD
                                pending_order = {} # Reset
                                missing_slot = None
                                continue

                        # --- Keyboard Fallback for QUANTITY ---
                        elif missing_slot == "quantity":
                            choice = get_keyboard_input("Enter quantity:")
                            try:
                                pending_order["quantity"] = int(choice)
                                missing_slot = None # Success!
                            except ValueError:
                                say_text("That's not a valid number. Cancelling order.")
                                current_state = STATE_LISTENING_FOR_WAKE_WORD
                                pending_order = {} # Reset
                                missing_slot = None
                                continue
                        
                        # --- Keyboard Fallback for SYMBOL ---
                        elif missing_slot == "symbol":
                            choice = get_keyboard_input("Enter stock name:")
                            pending_order["symbol"] = choice
                            missing_slot = None # Success!

                    # --- After processing the answer (by voice or keyboard),
                    #     we fall through to the slot-checking logic below.
                    
                else:
                    # --- We are processing a NEW COMMAND ---
                    transcription = transcribe_audio(TEMP_WAV_FILE)
                    if not transcription:
                        say_text("I didn't catch that. Please try again.")
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        continue
                        
                    pending_order = get_order_intent_gemini(transcription)
                    if not pending_order:
                        say_text("Sorry, I had trouble understanding the command.")
                        current_state = STATE_LISTENING_FOR_WAKE_WORD
                        continue

                # --- Slot Checking & Follow-up ---
                # This logic runs after a new command OR after filling a slot.
                
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
                
                # --- All slots are filled, now find the Security ID ---
                if "security_id" not in pending_order:
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
                        print(f"[StockFinder]: Matched to {id_result[1]}")
                        # Fall through to the final "Execute Order" step

                    else:
                        # --- More than one match: Ask for voice clarification ---
                        pending_order["options"] = id_results
                        option_names = []
                        for (id, name) in id_results:
                            # Speak first 3 words
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
                
                # Reset for the next command
                current_state = STATE_LISTENING_FOR_WAKE_WORD
                pending_order = {}
                missing_slot = None
                continue 

            elif current_state == STATE_AWAITING_ANSWER:
                # We've asked our question, now we just need to listen
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
# --- Standard Imports ---
import pvporcupine
import pyaudio
import struct
import vosk
import json

# --- New Imports for Security, API, Parsing, and Talk-Back ---
import os
from dotenv import load_dotenv
import pyttsx3
from dhan_handler import DhanHandler  # From your dhan_handler.py
from parser import parse_voice_command # From your parser.py

# --- 1. Load Keys and Initialize Handlers ---
print("Loading environment variables from .env...")
load_dotenv()

CLIENT_ID = os.getenv("DHAN_CLIENT_ID")
ACCESS_TOKEN = os.getenv("DHAN_ACCESS_TOKEN")

VOSK_VOCABULARY = [
    # Actions & Errors
    "buy", "by", "my", "sell", "cell",
    # Stocks & Errors
    "reliance", "audience", "rely on",
    "infosys", "infy",
    "tcs",
    "orient",
    # Numbers (Expanded to include all words up to 99)
    "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
    "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety",
    "hundred", "thousand",
    # Keywords
    "share", "shares", "at", "of"
]

VOSK_VOCAB_JSON = json.dumps(VOSK_VOCABULARY)

if not CLIENT_ID or not ACCESS_TOKEN:
    print("FATAL ERROR: DHAN_CLIENT_ID or DHAN_ACCESS_TOKEN not found in .env file.")
    print("Please create a .env file with your keys.")
    exit()

try:
    dhan_api = DhanHandler(CLIENT_ID, ACCESS_TOKEN)
except Exception as e:
    print(f"FATAL ERROR: Failed to initialize Dhan Handler: {e}")
    exit()

# --- 2. Initialize Talk-Back Engine ---
try:
    tts_engine = pyttsx3.init()
    tts_engine.setProperty('rate', 180) # Speaking speed
    print("Text-to-Speech engine initialized.")
except Exception as e:
    print(f"Warning: Failed to initialize TTS engine: {e}. App will run without talk-back.")
    tts_engine = None

def say_text(text):
    """Helper function for talk-back."""
    print(f"[Ledger]: {text}")
    if tts_engine:
        tts_engine.say(text)
        tts_engine.runAndWait()

# --- 3. Porcupine & Vosk Setup ---
# *** MAKE SURE THESE PATHS ARE CORRECT ***
ACCESS_KEY = "VaMKXo+5toOFwJisOb1CS7h28OK+HqtWKKNvQSUEDCfQVG6b+LjpYA==" 
KEYWORD_PATH = "/Users/vrajpatel/Downloads/Hey-Ledger_en_mac_v3_0_0/Hey-Ledger_en_mac_v3_0_0.ppn" 
VOSK_MODEL_PATH = "/Users/vrajpatel/Desktop/SBU/HCI/voice-trader/vosk-model-en-us-0.22" # Use your bigger model path

COMMAND_DURATION_SEC = 6 # How long to listen for a command

# --- 4. Initialize Vosk model ---
try:
    vosk.SetLogLevel(-1)
    vosk_model = vosk.Model(VOSK_MODEL_PATH)
    print("Vosk model loaded successfully.")
except Exception as e:
    print(f"FATAL ERROR: Error loading Vosk model: {e}")
    exit()

# --- 5. Initialize Porcupine ---
try:
    porcupine = pvporcupine.create(
        access_key=ACCESS_KEY,
        keyword_paths=[KEYWORD_PATH],
        sensitivities=[0.7]
    )
    print("Porcupine wake-word engine initialized.")
except Exception as e:
    print(f"FATAL ERROR: Error initializing Porcupine: {e}")
    exit()

# --- 6. Initialize PyAudio ---
pa = pyaudio.PyAudio()
try:
    audio_stream = pa.open(
        rate=porcupine.sample_rate,
        channels=1,
        format=pyaudio.paInt16,
        input=True,
        frames_per_buffer=porcupine.frame_length
    )
    print("Audio stream initialized.")
except IOError as e:
    print(f"FATAL ERROR: PyAudio Error: {e}")
    exit()


# --- 7. Main Application Loop ---
print("\nInitialization complete.")
say_text("Ledger is online and ready for commands.")
print("Press Ctrl+C to stop.")

try:
    while True: 
        # ===============================================================
        # --- STATE 1: WAITING FOR WAKE WORD (Porcupine)
        # ===============================================================
        print(f"\nListening for 'Hey Ledger'...")
        audio_stream.start_stream() # Start listening
        
        while True:
            pcm_bytes = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            pcm_unpacked = struct.unpack_from("h" * porcupine.frame_length, pcm_bytes)
            keyword_index = porcupine.process(pcm_unpacked)

            if keyword_index >= 0:
                print("---")
                print(">>> Wake word 'Hey Ledger' detected! <<<")
                say_text("I'm listening.")
                print(f"--- Listening for your command ({COMMAND_DURATION_SEC} seconds)...")
                break # --- Move to STATE 2 ---

        # ===============================================================
        # --- STATE 2: RECORD, PARSE, EXECUTE (Vosk -> Parser -> Dhan)
        # ===============================================================
        
        # 1. Record Audio
        recorded_frames = []
        frames_to_record = int((porcupine.sample_rate / porcupine.frame_length) * COMMAND_DURATION_SEC)
        
        for _ in range(frames_to_record):
            pcm_bytes = audio_stream.read(porcupine.frame_length, exception_on_overflow=False)
            recorded_frames.append(pcm_bytes)
        
        print("...Processing command...")
        
        # 2. Transcribe with Vosk
        recognizer = vosk.KaldiRecognizer(vosk_model, porcupine.sample_rate, VOSK_VOCAB_JSON)
        for frame in recorded_frames:
            recognizer.AcceptWaveform(frame)
        result_dict = json.loads(recognizer.FinalResult())
        command_text = result_dict.get('text', '')

        if command_text:
            print(f"You said: {command_text}")
            
            # 3. Parse with your new module
            parsed_order = parse_voice_command(command_text)
            
            if parsed_order:
                # 4. Execute with your new module
                response_message = dhan_api.place_voice_order(parsed_order)
                
                # 5. Talk-Back with the result
                say_text(response_message)
            else:
                say_text(f"Sorry, I didn't understand the command: {command_text}")
        else:
            say_text("I didn't catch that. Please try again.")

        # Clear the audio buffer
        audio_stream.stop_stream() 

except KeyboardInterrupt:
    print("\nStopping...")
finally:
    if 'audio_stream' in locals() and audio_stream:
        audio_stream.stop_stream()
        audio_stream.close()
    if 'porcupine' in locals() and porcupine:
        porcupine.delete()
    if 'pa' in locals() and pa:
        pa.terminate()
    print("Cleanup complete. Exiting.")
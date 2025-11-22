import os
import wave
import pyaudio
from google.cloud import speech
from elevenlabs import ElevenLabs, stream

# --- 1. Initialize Clients ---

# Google Speech-to-Text (STT)
try:
    speech_client = speech.SpeechClient()
    print("[Google STT]: Client initialized.")
except Exception as e:
    print(f"FATAL ERROR: Google STT init failed: {e}")

# ElevenLabs Text-to-Speech (TTS)
try:
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    if not ELEVENLABS_API_KEY:
        print("FATAL ERROR: ELEVENLABS_API_KEY not found in .env file.")
        exit()
    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    print("[ElevenLabs TTS]: Client initialized.")
except Exception as e:
    print(f"FATAL ERROR: ElevenLabs init failed: {e}")


# ==========================================
#  SECTION A: WEB SERVER FUNCTIONS (For server.py)
# ==========================================

def generate_audio_bytes(text: str) -> bytes:
    """
    Generates audio bytes using ElevenLabs.
    Returns raw bytes to be sent to the Frontend (Browser).
    """
    print(f"[TTS]: Generating audio for: '{text}'")
    try:
        # Convert text to audio generator
        audio_generator = eleven_client.text_to_speech.convert(
            text=text,
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel
            model_id="eleven_multilingual_v2"
        )
        # Consume generator to get full byte string
        audio_bytes = b"".join(audio_generator)
        return audio_bytes
    except Exception as e:
        print(f"[TTS]: Generation Error: {e}")
        return b""

def transcribe_audio_bytes(audio_content: bytes) -> str:
    """
    Transcribes raw audio bytes received from the Frontend.
    """
    try:
        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000, # Browser must send 16k wav
            language_code="en-IN",
        )
        
        response = speech_client.recognize(config=config, audio=audio)
        
        if response.results:
            transcription = response.results[0].alternatives[0].transcript
            print(f"[STT]: Result: '{transcription}'")
            return transcription
        return ""
    except Exception as e:
        print(f"[STT]: Error: {e}")
        return ""


# ==========================================
#  SECTION B: LOCAL TERMINAL FUNCTIONS (For main.py)
# ==========================================

def say_text(text: str):
    """
    Speaks text locally on the server/laptop speakers.
    """
    print(f"[Ledger]: {text}")
    try:
        audio_stream = eleven_client.text_to_speech.convert(
            text=text,
            voice_id="21m00Tcm4TlvDq8ikWAM",
            model_id="eleven_multilingual_v2"
        )
        stream(audio_stream)
    except Exception as e:
        print(f"ElevenLabs TTS Error: {e}")

def record_audio(duration_sec, file_path, audio_stream, frame_length, sample_rate):
    """
    Records audio from the local microphone.
    """
    print(f"Recording for {duration_sec} seconds...")
    frames = []
    num_frames = int((sample_rate / frame_length) * duration_sec)
    
    for _ in range(num_frames):
        try:
            data = audio_stream.read(frame_length, exception_on_overflow=False)
            frames.append(data)
        except IOError:
            pass
    
    wf = wave.open(file_path, 'wb')
    wf.setnchannels(1)
    wf.setsampwidth(pyaudio.PyAudio().get_sample_size(pyaudio.paInt16))
    wf.setframerate(sample_rate)
    wf.writeframes(b''.join(frames))
    wf.close()
    print(f"Audio saved to {file_path}")

def transcribe_audio(file_path: str, sample_rate: int) -> str:
    """
    Transcribes a local .wav file.
    """
    print(f"Sending {file_path} to Google STT...")
    try:
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
        
        # Re-use the byte transcriber logic to avoid duplication code
        return transcribe_audio_bytes(content)
        
    except Exception as e:
        print(f"Google STT Error: {e}")
        return ""
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
    print(f"FATAL ERROR: Could not initialize Google Speech Client: {e}")
    print("Please ensure 'GOOGLE_APPLICATION_CREDENTIALS' is set correctly.")
    exit()

# ElevenLabs Text-to-Speech (TTS)
try:
    ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")
    if not ELEVENLABS_API_KEY:
        print("FATAL ERROR: ELEVENLABS_API_KEY not found in .env file.")
        exit()
    eleven_client = ElevenLabs(api_key=ELEVENLABS_API_KEY)
    print("[ElevenLabs TTS]: Client initialized.")
except Exception as e:
    print(f"FATAL ERROR: Could not initialize ElevenLabs: {e}")
    exit()

# --- 2. Audio Functions ---

def say_text(text: str):
    """
    Speaks text using the ElevenLabs TTS engine.
    """
    print(f"[Ledger]: {text}")
    try:
        audio_stream = eleven_client.text_to_speech.convert(
            text=text,
            voice_id="21m00Tcm4TlvDq8ikWAM",  # Rachel's voice ID
            model_id="eleven_multilingual_v2"
        )
        stream(audio_stream) # This handles playback automatically
        
    except Exception as e:
        print(f"ElevenLabs TTS Error: {e}")

def record_audio(duration_sec, file_path, audio_stream, frame_length, sample_rate):
    """
    Records audio from the stream for a set duration and saves to file.
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
    Sends a local audio file to Google Cloud Speech-to-Text.
    """
    print(f"Sending {file_path} to Google STT...")
    try:
        with open(file_path, "rb") as audio_file:
            content = audio_file.read()
        
        audio = speech.RecognitionAudio(content=content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
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

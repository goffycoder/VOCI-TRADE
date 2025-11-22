import requests
import base64
import os
import time

# URL of your running server
SERVER_URL = "http://localhost:8000/chat"

def send_command(text):
    print(f"\n--- Sending: '{text}' ---")
    
    try:
        # 1. Send POST request to server
        payload = {"message": text, "context": {}}
        response = requests.post(SERVER_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            # 2. Print Text Response
            print(f"Bot Says: {data['text']}")
            
            # 3. Save Audio to file
            audio_data = base64.b64decode(data['audio_base64'])
            with open("response.mp3", "wb") as f:
                f.write(audio_data)
            
            # 4. Play Audio (Mac command, change to 'start' for Windows)
            os.system("afplay response.mp3") 
            
            # Optional: Print Data Payload (debug info)
            if data.get('data'):
                print(f"Debug Data: {data['data']}")
        else:
            print(f"Error: Server returned {response.status_code}")
            print(response.text)
            
    except Exception as e:
        print(f"Connection Error: Is server.py running? {e}")

if __name__ == "__main__":
    print("Type your command (or 'exit' to quit)")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ["exit", "quit"]:
            break
        send_command(user_input)
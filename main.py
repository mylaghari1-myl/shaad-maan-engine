python
import os
import base64
import requests
from fastapi import FastAPI, Request, Response
from google import genai

app = FastAPI()

# Initializing official Google GenAI Client
client = genai.Client()

META_TOKEN = os.environ.get("META_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.environ.get("META_PHONE_NUMBER_ID")
VERIFY_TOKEN = "MyDaughterProjectToken2026"

@app.get("/webhook")
def verify_meta(request: Request):
    """Initial validation gate for Meta's verification webhook"""
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return "Token Validation Failure"

@app.post("/webhook")
async def handle_whatsapp_message(request: Request):
    """Processes real-time inbound text and voice notifications from Meta"""
    payload = await request.json()
    
    try:
        entry = payload["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        message = value["messages"][0]
        sender_phone = message["from"]
        
        # Intercept and process voice logs natively
        if message.get("type") == "audio":
            audio_id = message["audio"]["id"]
            
            # Step A: Download temporary media locator from Meta Cloud
            headers = {"Authorization": f"Bearer {META_TOKEN}"}
            media_info = requests.get(f"https://graph.facebook.com/v25.0/{audio_id}", headers=headers).json()
            download_url = media_info.get("url")
            
            # Step B: Get raw audio stream data binary
            raw_audio_bytes = requests.get(download_url, headers=headers).content
            
            # Step C: Send direct inline media request to Gemini 2.5 Flash
            ai_response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=[
                    "You are a helpful, warm AI conversational assistant. Listen to the audio and reply naturally back in the user's language.",
                    {"inline_data": {"data": base64.b64encode(raw_audio_bytes).decode('utf-8'), "mime_type": "audio/ogg"}}
                ]
            )
            
            # Step D: Route structured text feedback to target user channel
            send_whatsapp_text(sender_phone, ai_response.text)
            
    except Exception:
        pass
    return {"status": "success"}

def send_whatsapp_text(phone_number, reply_text):
    """Transmits structural messages to active chat pipelines via Graph API"""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {META_TOKEN}", "Content-Type": "application/json"}
    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "text",
        "text": {"body": reply_text}
    }
    requests.post(url, json=data, headers=headers)

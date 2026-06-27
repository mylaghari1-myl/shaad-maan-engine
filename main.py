import os
import requests
from fastapi import FastAPI, Request, Response, HTTPException, status
from google import genai

# 1. Initialize FastAPI App
app = FastAPI()

# 2. Grab Environment Variables from Render Dashboard
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "MyDaughterProjectToken2026")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# 3. Initialize Gemini Client
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None

# --- Webhook Authentication Endpoint (GET) ---
@app.get("/webhook")
@app.get("/webhook/")
async def verify_webhook(request: Request):
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("=== WEBHOOK VERIFIED SUCCESSFULLY ===")
            return Response(content=challenge, media_type="text/plain")
        else:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Verification token mismatch.")
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing webhook parameters.")


# --- Handle Incoming Messages Endpoint (POST) ---
@app.post("/webhook")
@app.post("/webhook/")
async def receive_whatsapp_message(request: Request):
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    if not (body.get("object") == "whatsapp_business_account" and "entry" in body):
        return {"status": "ignored", "reason": "Not a valid WhatsApp event structure"}

    try:
        entry = body["entry"][0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if not messages:
            return {"status": "ignored", "reason": "No new messages found in entry payload"}

        msg = messages[0]
        from_number = msg.get("from")
        msg_type = msg.get("type")

        if msg_type == "text":
            user_text = msg["text"].get("body", "")
            print(f"Received text from {from_number}: {user_text}")

            if ai_client:
                response = ai_client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=user_text,
                )
                reply_text = response.text
            else:
                reply_text = "System configuration error: Gemini API key is missing."

            send_whatsapp_text(from_number, reply_text)

        elif msg_type == "audio":
            audio_id = msg["audio"].get("id")
            print(f"Received voice note ID {audio_id} from {from_number}")
            reply_text = "پیغام موصول ہوا۔ ہماری آڈیو پروسیسنگ پائپ لائن فی الحال کام کر رہی ہے۔"
            send_whatsapp_text(from_number, reply_text)

        else:
            print(f"Unsupported message type received: {msg_type}")

    except Exception as e:
        print(f"Error handling webhook event: {str(e)}")
        return {"status": "error", "message": str(e)}

    return {"status": "success"}


def send_whatsapp_text(recipient_number: str, message_text: str):
    if not WHATSAPP_TOKEN or not PHONE_NUMBER_ID:
        print("Error: Meta credentials missing from Environment variables.")
        return

    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": recipient_number,
        "type": "text",
        "text": {"preview_url": False, "body": message_text}
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code not in [200, 201]:
        print(f"Meta API Error: {response.status_code} - {response.text}")
    else:
        print(f"Message cleanly dispatched to {recipient_number}")

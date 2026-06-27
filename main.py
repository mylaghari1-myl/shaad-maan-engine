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

# 3. Initialize Gemini Client (Using the official google-genai SDK format)
if GEMINI_API_KEY:
    ai_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    ai_client = None


# --- Webhook Authentication Endpoint (GET) ---
# Dual-route decorators explicitly resolve forced trailing slashes by Meta's validation engine
@app.get("/webhook")
@app.get("/webhook/")
async def verify_webhook(request: Request):
    """
    Handles the initial registration handshake from Meta.
    """
    params = request.query_params
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            print("=== WEBHOOK VERIFIED SUCCESSFULLY ===")
            return Response(content=challenge, media_type="text/plain")
        else:
            print(f"Verification Failed. Expected: {VERIFY_TOKEN}, Received: {token}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Verification token mismatch."
            )
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST, 
        detail="Missing webhook parameters."
    )


# --- Handle Incoming Messages Endpoint (POST) ---
@app.post("/webhook")
            # Localized default acknowledgement response
            reply_text = "پیغام موصول ہوا۔ ہماری آڈیو پروسیسنگ پائپ لائن فی الحال کام کر رہی ہے۔"
            send_whatsapp_text(from_number, reply_text)

        else:
            print(f"Unsupported message type received: {msg_type}")

    except Exception as e:
        print(f"Error handling webhook event: {str(e)}")
        # Return a 200 OK status regardless to prevent Meta from looping retries on failed instances
        return {"status": "error", "message": str(e)}

    return {"status": "success"}


def send_whatsapp_text(recipient_number: str, message_text: str):
    """
    Dispatches outbound text messages via Meta Cloud API v18.0
    """
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

# Port-binding execution block is omitted intentionally.
# Render native configuration uses Uvicorn externally via the dashboard Start Command.

import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

# -------- LOAD ENV --------
load_dotenv()

TOKEN = os.getenv("TOKEN")

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RENDER_URL")
if not RENDER_URL:
    RENDER_URL = "https://your-app.onrender.com"

app = Flask(__name__)

# -------- DESTINATIONS --------
DESTINATIONS = {
    "tokyo": "NRT",
    "japan": "NRT",
    "osaka": "KIX",
    "bangkok": "BKK",
    "thailand": "BKK",
    "singapore": "SIN",
    "seoul": "ICN",
    "korea": "ICN",
    "hong kong": "HKG",
    "taipei": "TPE"
}

# -------- TELEGRAM --------
def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": text,
        "disable_web_page_preview": False
    }

    if buttons:
        payload["reply_markup"] = {
            "inline_keyboard": buttons
        }

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# -------- WEBHOOK SET --------
def set_webhook():
    if not TOKEN:
        return

    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    try:
        requests.post(url, json={"url": f"{RENDER_URL}/{TOKEN}"})
    except Exception as e:
        print("Webhook error:", e)

# -------- PARSE DESTINATION --------
def extract_destination(text):
    text = text.lower()
    for key, iata in DESTINATIONS.items():
        if key in text:
            return key, iata
    return None, None

# -------- GOOGLE FLIGHTS LINK --------
def build_flight_link(iata):
    return (
        "https://www.google.com/travel/flights?q="
        f"Flights%20from%20MNL%20to%20{iata}%20from%20Philippines"
    )

# -------- MAIN LOGIC --------
def process_flight(chat_id, dest_key, iata):
    send_message(chat_id, f"🔍 Searching flights to {dest_key.title()}...")

    link = build_flight_link(iata)

    msg = (
        f"✈️ Flight Search Ready!\n\n"
        f"📍 Route: MNL → {iata}\n\n"
        f"💡 Live prices are available below:"
    )

    buttons = [[
        {
            "text": f"Open Google Flights ✈️",
            "url": link
        }
    ]]

    send_message(chat_id, msg, buttons)

# -------- WEBHOOK --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()

        if not data or "message" not in data:
            return "OK", 200

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        dest_key, iata = extract_destination(text)

        if not iata:
            send_message(
                chat_id,
                "❌ Try:\n• Japan\n• Thailand\n• Korea\n• Singapore\n\nExample: flights to Japan"
            )
            return "OK", 200

        process_flight(chat_id, dest_key, iata)

        return "OK", 200

    except Exception as e:
        print("Webhook error:", e)
        return "OK", 200

# -------- HOME --------
@app.route("/", methods=["GET"])
def home():
    set_webhook()
    return "✅ Bot running", 200

# -------- START --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
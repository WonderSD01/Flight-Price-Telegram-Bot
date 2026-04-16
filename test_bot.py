import os
import requests
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# -------- LOAD ENV --------
load_dotenv()

TOKEN = os.getenv("TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

# Auto-detect Render URL
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RENDER_URL")

if not RENDER_URL:
    print("⚠️ No RENDER URL found, using fallback")
    RENDER_URL = "https://flight-price-telegram-bot.onrender.com"

if not TOKEN:
    print("❌ WARNING: TOKEN missing")
if not SERPAPI_KEY:
    print("❌ WARNING: SERPAPI_KEY missing")

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
def send_message(chat_id, text):
    if not TOKEN:
        print("❌ Cannot send message, TOKEN missing")
        return

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": chat_id,
            "text": text
        }, timeout=10)
        print("📤 Telegram:", res.text)
    except Exception as e:
        print("❌ Telegram error:", e)

def set_webhook():
    if not TOKEN:
        return

    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"

    try:
        res = requests.post(url, json={"url": webhook_url})
        print("🔗 Webhook:", res.text)
    except Exception as e:
        print("❌ Webhook error:", e)

# -------- DESTINATION PARSER --------
def extract_destination(text):
    text = text.lower()
    for key in DESTINATIONS:
        if key in text:
            return key, DESTINATIONS[key]
    return None, None

# -------- FLIGHT SEARCH --------
def get_flight(iata):
    if not SERPAPI_KEY:
        return None

    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": "MNL",
        "arrival_id": iata,
        "outbound_date": "2026-08-15",
        "currency": "PHP",
        "hl": "en",
        "api_key": SERPAPI_KEY
    }

    try:
        res = requests.get(url, params=params, timeout=25)
        data = res.json()

        print("🧪 SerpAPI:", data)

        if "error" in data:
            return None

        flights = data.get("best_flights") or data.get("other_flights") or []
        if not flights:
            return None

        top = flights[0]

        airline = top.get("flights", [{}])[0].get("airline", "Unknown")
        price = top.get("price", "N/A")

        return {
            "airline": airline,
            "price": price,
            "iata": iata
        }

    except Exception as e:
        print("❌ Flight error:", e)
        return None

# -------- BACKGROUND TASK --------
def process_flight(chat_id, dest_key, iata):
    send_message(chat_id, f"🔍 Searching flights to {dest_key.title()}...")

    result = get_flight(iata)

    if result:
        price = result["price"]
        price_str = f"₱{price:,}" if isinstance(price, (int, float)) else str(price)

        msg = (
            f"✈️ Cheapest Flight Found!\n\n"
            f"📍 MNL → {result['iata']}\n"
            f"🛫 Airline: {result['airline']}\n"
            f"💰 Price: {price_str}\n"
            f"📅 Date: Aug 15, 2026"
        )
    else:
        msg = f"❌ No flights found for {dest_key.title()}."

    send_message(chat_id, msg)

# -------- WEBHOOK --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        print("📩 Incoming:", data)

        if not data or "message" not in data:
            return "OK", 200

        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")

        dest_key, iata = extract_destination(text)

        if not iata:
            send_message(chat_id,
                "❌ Try:\n• Japan\n• Tokyo\n• Bangkok\n• Seoul\n\nExample: cheap flights to japan"
            )
            return "OK", 200

        # Run in background (prevents timeout)
        thread = threading.Thread(
            target=process_flight,
            args=(chat_id, dest_key, iata)
        )
        thread.start()

        return "OK", 200

    except Exception as e:
        print("❌ Webhook error:", e)
        return "OK", 200

# -------- HEALTH --------
@app.route("/", methods=["GET"])
def home():
    set_webhook()
    return "✅ Bot is running!", 200

# -------- START --------
if __name__ == "__main__":
    print("🚀 Bot starting...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
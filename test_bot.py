import os
import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

# -------- LOAD ENV --------
load_dotenv()
TOKEN = os.getenv("TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
RENDER_URL = os.getenv("https://flight-price-telegram-bot.onrender.com")  # set this in Render

if not TOKEN:
    raise ValueError("❌ TOKEN is missing")
if not SERPAPI_KEY:
    raise ValueError("❌ SERPAPI_KEY is missing")
if not RENDER_URL:
    raise ValueError("❌ RENDER_URL is missing")

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
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        res = requests.post(url, json={
            "chat_id": chat_id,
            "text": text
        }, timeout=10)
        print("📤 Telegram response:", res.text)
    except Exception as e:
        print("❌ Telegram send error:", e)

def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook"
    try:
        res = requests.post(url, json={"url": webhook_url})
        print("🔗 Webhook set:", res.text)
    except Exception as e:
        print("❌ Webhook error:", e)

# -------- HELPER: FIND DESTINATION --------
def extract_destination(user_text):
    user_text = user_text.lower()
    for key in DESTINATIONS:
        if key in user_text:
            return key, DESTINATIONS[key]
    return None, None

# -------- FLIGHT SEARCH --------
def get_flight(iata):
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

        print("🧪 SerpAPI response:", data)

        if "error" in data:
            print("❌ SerpAPI error:", data["error"])
            return None

        flights = data.get("best_flights") or data.get("other_flights") or []

        if not flights:
            return None

        top = flights[0]

        airline = (
            top.get("flights", [{}])[0].get("airline", "Unknown")
        )

        price = top.get("price", "N/A")

        return {
            "price": price,
            "airline": airline,
            "iata": iata
        }

    except Exception as e:
        print("❌ Flight fetch error:", e)
        return None

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

        # Find destination
        dest_key, iata = extract_destination(text)

        if not iata:
            send_message(chat_id,
                "❌ I didn’t understand.\n\nTry:\n• Japan\n• Tokyo\n• Bangkok\n• Seoul"
            )
            return "OK", 200

        send_message(chat_id, f"🔍 Searching flights to {dest_key.title()}...")

        result = get_flight(iata)

        if result:
            price = result["price"]

            if isinstance(price, (int, float)):
                price_str = f"₱{price:,}"
            else:
                price_str = str(price)

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

        return "OK", 200

    except Exception as e:
        print("❌ Webhook error:", e)
        return "OK", 200

# -------- ROOT --------
@app.route("/", methods=["GET"])
def home():
    set_webhook()
    return "✅ Bot is running!", 200

# -------- START --------
if __name__ == "__main__":
    print("🚀 Starting bot...")
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
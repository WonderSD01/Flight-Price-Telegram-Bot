import os
import requests
from flask import Flask, request
from dotenv import load_dotenv

# -------- LOAD ENV --------
load_dotenv()
TOKEN = os.getenv("TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")
RENDER_URL = "https://flight-price-telegram-bot.onrender.com"

app = Flask(__name__)

# -------- DATA DICTIONARIES (Simplified for Speed) --------
# We use only the main airport for each to keep it fast
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

# -------- TELEGRAM HELPERS --------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

def set_webhook():
    webhook_url = f"{RENDER_URL}/{TOKEN}"
    url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
    requests.get(url)

# -------- FLIGHT SEARCH (Simplified) --------
def get_flight(iata):
    """Checks Google Flights for one specific airport."""
    url = "https://serpapi.com/search"
    params = {
        "engine": "google_flights",
        "departure_id": "MNL",
        "arrival_id": iata,
        "outbound_date": "2026-08-15", # Further date for better availability
        "currency": "PHP",
        "hl": "en",
        "api_key": SERPAPI_KEY
    }
    
    try:
        # We use a 15-second timeout to prevent Render from hanging
        response = requests.get(url, params=params, timeout=15)
        data = response.json()
        
        # Look for flights in 'best_flights' or 'other_flights'
        flights = data.get("best_flights", []) or data.get("other_flights", [])
        
        if flights:
            top = flights[0]
            return {
                "price": top.get("price"),
                "airline": top["flights"][0].get("airline"),
                "iata": iata
            }
    except Exception as e:
        print(f"Error: {e}")
    return None

# -------- WEBHOOK ROUTE --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    if not data or "message" not in data: return "OK", 200

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "").lower().strip()

    # 1. Check if we support the destination
    iata = DESTINATIONS.get(text)
    if not iata:
        send_message(chat_id, "❌ Try 'Japan' or 'Bangkok'.")
        return "OK", 200

    # 2. Start Search
    send_message(chat_id, f"🔍 Checking Manila to {text.title()}...")
    
    # 3. Get Result
    result = get_flight(iata)

    if result:
        price = result['price']
        # If it's a number, format it with ₱
        price_str = f"₱{price:,}" if isinstance(price, (int, float)) else price
        
        msg = (f"✈️ Cheapest Found!\n\n"
               f"📍 MNL → {result['iata']}\n"
               f"🛫 Airline: {result['airline']}\n"
               f"💰 Price: {price_str}\n"
               f"📅 Date: Aug 15, 2026")
    else:
        msg = f"❌ No flights found for {text.title()} on that date."

    send_message(chat_id, msg)
    return "OK", 200

# -------- HOME ROUTE --------
@app.route('/')
def index():
    set_webhook()
    return "Bot is Active!", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
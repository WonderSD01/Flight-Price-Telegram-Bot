import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# -------- LOAD ENV --------
load_dotenv()
TOKEN = os.getenv("TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

# Replace this with your actual Render URL
RENDER_URL = "https://flight-price-telegram-bot.onrender.com"
ORIGIN = "MNL"  

app = Flask(__name__)

# -------- DATA DICTIONARIES --------
CITY_AIRPORTS = {
    "tokyo": ["NRT", "HND"],
    "osaka": ["KIX"],
    "bangkok": ["BKK"],
    "singapore": ["SIN"],
    "seoul": ["ICN"],
    "hong kong": ["HKG"],
    "taipei": ["TPE"]
}

COUNTRY_AIRPORTS = {
    "japan": ["NRT", "HND", "KIX"],
    "korea": ["ICN", "PUS"],
    "thailand": ["BKK", "HKT"],
    "taiwan": ["TPE", "KHH"],
    "vietnam": ["SGN", "HAN"]
}

# -------- TELEGRAM HELPERS --------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Error sending message: {e}")

def set_webhook():
    if RENDER_URL and TOKEN:
        webhook_url = f"{RENDER_URL}/{TOKEN}"
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        res = requests.get(url)
        print(f"✅ Webhook setup attempt: {res.json()}")

# -------- FLIGHT SEARCH LOGIC --------
def search_flight(dest_iata):
    """Calls the SkyScrapper API for a single IATA code."""
    url = "https://sky-scrapper.p.rapidapi.com/api/v1/flights/searchFlights"
    # Note: Using hardcoded dates for this example; 
    # In a real bot, you'd ask the user for a date!
    querystring = {
        "originSkyId": ORIGIN,
        "destinationSkyId": dest_iata,
        "originEntityId": "95673398", # MNL Entity ID
        "destinationEntityId": "95673321", # Example Default
        "date": "2026-06-15",
        "cabinClass": "economy",
        "adults": "1",
        "currency": "PHP"
    }

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "sky-scrapper.p.rapidapi.com"
    }

    try:
        response = requests.get(url, headers=headers, params=querystring, timeout=15)
        data = response.json()
        if data.get("status") and data["data"].get("itineraries"):
            cheapest = data["data"]["itineraries"][0]
            return {
                "price": cheapest["price"]["raw"],
                "airline": cheapest["legs"][0]["carriers"]["marketing"][0]["name"],
                "iata": dest_iata
            }
    except Exception as e:
        print(f"Error searching {dest_iata}: {e}")
    return None

def get_iata_codes(user_input):
    """Returns a list of IATA codes based on city or country."""
    if user_input in CITY_AIRPORTS:
        return CITY_AIRPORTS[user_input]
    if user_input in COUNTRY_AIRPORTS:
        return COUNTRY_AIRPORTS[user_input]
    return []

def find_cheapest(iata_list):
    """Searches multiple airports in parallel to save time."""
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(search_flight, iata_list))
    
    valid_results = [r for r in results if r is not None]
    if not valid_results:
        return None
    return min(valid_results, key=lambda x: x["price"])

# -------- WEBHOOK ROUTE --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    if not data or "message" not in data:
        return "OK", 200

    message = data["message"]
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "").lower().strip()

    if not text or not chat_id:
        return "OK", 200

    # 1. Get IATA codes
    iata_codes = get_iata_codes(text)

    if not iata_codes:
        send_message(chat_id, "❌ Sorry, I don't recognize that destination. Try 'Japan' or 'Bangkok'.")
        return "OK", 200

    # 2. Inform user search has started
    send_message(chat_id, f"🔍 Searching for the cheapest flights to {text.title()}...")

    # 3. Find cheapest and reply
    result = find_cheapest(iata_codes)

    if result:
        reply = (f"✈️ Cheapest Flight Found!\n\n"
                 f"📍 Manila (MNL) → {result['iata']}\n"
                 f"🛫 Airline: {result['airline']}\n"
                 f"💰 Price: ₱{result['price']:,}\n"
                 f"📅 Date: 2026-06-15")
    else:
        reply = f"❌ Sorry, I couldn't find any flights for {text.title()} right now."

    send_message(chat_id, reply)
    return "OK", 200

# -------- HOME ROUTE (Activation) --------
@app.route('/')
def index():
    set_webhook()
    return "<h1>Bot is running!</h1><p>Webhook has been refreshed.</p>", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
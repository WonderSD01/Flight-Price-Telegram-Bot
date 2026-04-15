import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# -------- LOAD ENV --------
load_dotenv()
TOKEN = os.getenv("TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
# Render provides a dynamic URL. Replace this with your Render URL after creating the service.
RENDER_URL = os.getenv("https://flight-price-telegram-bot.onrender.com") 

ORIGIN = "MNL"  

app = Flask(__name__)

# ... (Keep your CITY_AIRPORTS and COUNTRY_AIRPORTS dictionaries here) ...

# -------- TELEGRAM HELPERS --------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": text})

def set_webhook():
    if RENDER_URL:
        webhook_url = f"{RENDER_URL}/{TOKEN}"
        url = f"https://api.telegram.org/bot{TOKEN}/setWebhook?url={webhook_url}"
        requests.get(url)
        print(f"✅ Webhook set to: {webhook_url}")

# ... (Keep your get_iata_codes, search_flight, and find_cheapest functions here) ...

# -------- WEBHOOK ROUTE --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    if not text or not chat_id:
        return "OK", 200

    # Process logic (Searching flights...)
    user_input = text.lower().strip()
    iata_codes = get_iata_codes(user_input)

    if not iata_codes:
        send_message(chat_id, "❌ Destination not supported.")
        return "OK", 200

    send_message(chat_id, f"✈️ Searching flights to {text}...")
    result = find_cheapest(iata_codes)

    if result:
        reply = (f"✈️ Cheapest Flight Found!\n\n📍 Manila → {text}\n"
                 f"🛫 Airline: {result['airline']}\n💰 ₱{result['price']:,}")
    else:
        reply = f"❌ No flights found for {text}"

    send_message(chat_id, reply)
    return "OK", 200

# -------- HEALTH CHECK ROUTE --------
@app.route('/')
def index():
    set_webhook() # Tries to set webhook whenever the home page is visited
    return "Bot is running!", 200

if __name__ == "__main__":
    # Use port from environment variable for Render compatibility
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
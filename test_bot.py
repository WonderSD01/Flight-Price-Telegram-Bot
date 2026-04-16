import os
import requests
import threading
from datetime import datetime, timedelta
from flask import Flask, request
from dotenv import load_dotenv

# -------- LOAD ENV --------
load_dotenv()

TOKEN = os.getenv("TOKEN")
SERPAPI_KEY = os.getenv("SERPAPI_KEY")

RENDER_URL = os.getenv("RENDER_EXTERNAL_URL") or os.getenv("RENDER_URL")
if not RENDER_URL:
    print("⚠️ Using fallback URL")
    RENDER_URL = "https://flight-price-telegram-bot.onrender.com"

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
        print("❌ TOKEN missing")
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=10
        )
    except Exception as e:
        print("❌ Telegram error:", e)

def set_webhook():
    if not TOKEN:
        return

    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook",
            json={"url": f"{RENDER_URL}/{TOKEN}"}
        )
    except Exception as e:
        print("❌ Webhook error:", e)

# -------- DESTINATION --------
def extract_destination(text):
    text = text.lower()
    for key in DESTINATIONS:
        if key in text:
            return key, DESTINATIONS[key]
    return None, None

# -------- GENERATE MULTIPLE DATES --------
def get_dates():
    base = datetime.today() + timedelta(days=30)  # start 1 month ahead
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 10, 2)]
    # 5 dates: +0, +2, +4, +6, +8 days

# -------- FLIGHT SEARCH (MULTI-DATE) --------
def get_cheapest_flight(iata):
    if not SERPAPI_KEY:
        return None

    dates = get_dates()
    cheapest = None

    for date in dates:
        print(f"🔍 Checking date: {date}")

        params = {
            "engine": "google_flights",
            "departure_id": "MNL",
            "arrival_id": iata,
            "outbound_date": date,
            "currency": "PHP",
            "hl": "en",
            "api_key": SERPAPI_KEY
        }

        try:
            res = requests.get("https://serpapi.com/search", params=params, timeout=20)
            data = res.json()

            if "error" in data:
                print("❌ API error:", data["error"])
                continue

            flights = data.get("best_flights") or data.get("other_flights")
            if not flights:
                continue

            top = flights[0]

            price = top.get("price")
            airline = top.get("flights", [{}])[0].get("airline", "Unknown")

            if not isinstance(price, (int, float)):
                continue

            if cheapest is None or price < cheapest["price"]:
                cheapest = {
                    "price": price,
                    "airline": airline,
                    "iata": iata,
                    "date": date
                }

        except Exception as e:
            print("❌ Flight error:", e)

    return cheapest

# -------- BACKGROUND TASK --------
def process_flight(chat_id, dest_key, iata):
    send_message(chat_id, f"🔍 Finding cheapest flights to {dest_key.title()}...")

    result = get_cheapest_flight(iata)

    if result:
        msg = (
            f"✈️ Cheapest Flight Found!\n\n"
            f"📍 MNL → {result['iata']}\n"
            f"🛫 Airline: {result['airline']}\n"
            f"💰 Price: ₱{result['price']:,}\n"
            f"📅 Date: {result['date']}"
        )
    else:
        msg = (
            f"❌ No flights found for {dest_key.title()}.\n"
            f"💡 Try again later or another destination."
        )

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
                "❌ Try:\n• Japan\n• Thailand\n• Singapore\n\nExample: cheap flights to japan"
            )
            return "OK", 200

        threading.Thread(
            target=process_flight,
            args=(chat_id, dest_key, iata)
        ).start()

        return "OK", 200

    except Exception as e:
        print("❌ Webhook error:", e)
        return "OK", 200

# -------- ROOT --------
@app.route("/", methods=["GET"])
def home():
    set_webhook()
    return "✅ Bot running", 200

# -------- START --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
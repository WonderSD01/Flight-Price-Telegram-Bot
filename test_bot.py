import os
import requests
import threading
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
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
def send_message(chat_id, text, buttons=None):
    if not TOKEN:
        print("❌ TOKEN missing")
        return

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
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/sendMessage",
            json=payload,
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

# -------- DATE GENERATOR --------
def get_dates():
    base = datetime.today() + timedelta(days=30)
    return [(base + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(0, 10, 2)]

# -------- FETCH FLIGHTS PER DATE --------
def fetch_flights(iata, date):
    params = {
        "engine": "google_flights",
        "departure_id": "MNL",
        "arrival_id": iata,
        "outbound_date": date,
        "type": "2",  # one-way
        "adults": 1,
        "travel_class": "economy",
        "currency": "PHP",
        "hl": "en",
        "api_key": SERPAPI_KEY
    }

    try:
        res = requests.get("https://serpapi.com/search", params=params, timeout=20)
        data = res.json()

        if "error" in data:
            print("❌ API error:", data["error"])
            return []

        flights = data.get("best_flights") or data.get("other_flights") or []

        results = []
        for f in flights[:3]:
            price = f.get("price")
            airline = f.get("flights", [{}])[0].get("airline", "Unknown")

            # Get real link if available
            link = f.get("link")

            # Fallback Google Flights link
            if not link:
                link = f"https://www.google.com/travel/flights?hl=en#flt=MNL.{iata}.{date}"

            if isinstance(price, (int, float)):
                results.append({
                    "price": price,
                    "airline": airline,
                    "date": date,
                    "iata": iata,
                    "link": link
                })

        return results

    except Exception as e:
        print("❌ Fetch error:", e)
        return []

# -------- PARALLEL SEARCH --------
def get_best_flights(iata):
    dates = get_dates()
    all_flights = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(fetch_flights, iata, d) for d in dates]

        for future in as_completed(futures):
            results = future.result()
            if results:
                all_flights.extend(results)

    if not all_flights:
        return None

    all_flights.sort(key=lambda x: x["price"])
    return all_flights[:3]

# -------- PROCESS --------
def process_flight(chat_id, dest_key, iata):
    send_message(chat_id, f"🔍 Finding best flights to {dest_key.title()}...")

    results = get_best_flights(iata)

    if not results:
        send_message(chat_id,
            f"❌ No flights found for {dest_key.title()}.\nTry again later."
        )
        return

    msg = "✈️ Top Cheapest Flights:\n\n"
    buttons = []

    for i, f in enumerate(results, 1):
        msg += (
            f"{i}. 💰 ₱{f['price']:,}\n"
            f"   🛫 {f['airline']}\n"
            f"   📅 {f['date']}\n\n"
        )

        # Add button for each flight
        buttons.append([{
            "text": f"Book #{i} ✈️",
            "url": f["link"]
        }])

    send_message(chat_id, msg, buttons)

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
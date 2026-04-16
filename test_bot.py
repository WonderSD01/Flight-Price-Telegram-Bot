import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from datetime import datetime, timedelta

# -------- LOAD ENV --------
load_dotenv()

TOKEN = os.getenv("TOKEN")
KIWI_API_KEY = os.getenv("KIWI_API_KEY")  # optional but recommended

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
        payload["reply_markup"] = {"inline_keyboard": buttons}

    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print("Telegram error:", e)

# -------- WEBHOOK --------
def set_webhook():
    try:
        requests.post(
            f"https://api.telegram.org/bot{TOKEN}/setWebhook",
            json={"url": f"{RENDER_URL}/{TOKEN}"}
        )
    except Exception as e:
        print("Webhook error:", e)

# -------- PARSE DESTINATION --------
def extract_destination(text):
    text = text.lower()
    for k, v in DESTINATIONS.items():
        if k in text:
            return k, v
    return None, None

# -------- DATE RANGE (SKYSCANNER STYLE FLEXIBILITY) --------
def get_dates():
    base = datetime.today() + timedelta(days=15)
    return [(base + timedelta(days=i)).strftime("%d/%m/%Y") for i in range(0, 10, 2)]

# -------- KIWI API (REAL FLIGHT DATA) --------
def fetch_kiwi(iata):
    if not KIWI_API_KEY:
        return None

    url = "https://tequila-api.kiwi.com/v2/search"

    headers = {"apikey": KIWI_API_KEY}

    params = {
        "fly_from": "MNL",
        "fly_to": iata,
        "date_from": get_dates()[0],
        "date_to": get_dates()[-1],
        "limit": 5,
        "curr": "PHP",
        "sort": "price"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=20)
        data = res.json()

        flights = data.get("data", [])
        results = []

        for f in flights:
            results.append({
                "price": f.get("price"),
                "airline": f.get("airlines", ["Unknown"])[0],
                "link": f.get("deep_link")
            })

        return results

    except Exception as e:
        print("Kiwi error:", e)
        return None

# -------- FALLBACK (ALWAYS WORKS) --------
def fallback_results(iata):
    return [{
        "price": None,
        "airline": "Search Live Prices",
        "link": f"https://www.google.com/travel/flights?q=Flights%20from%20MNL%20to%20{iata}"
    }]

# -------- MAIN ENGINE --------
def get_flights(iata):
    results = fetch_kiwi(iata)

    if results and len(results) > 0:
        return results[:3]

    return fallback_results(iata)

# -------- PROCESS --------
def process_flight(chat_id, dest_key, iata):
    send_message(chat_id, f"✈️ Searching best deals to {dest_key.title()}...")

    flights = get_flights(iata)

    msg = f"✈️ Best Flights: MNL → {iata}\n\n"
    buttons = []

    for i, f in enumerate(flights, 1):
        price = f["price"]

        price_text = f"₱{price:,}" if price else "Check live price"

        msg += (
            f"{i}. 💰 {price_text}\n"
            f"   🛫 {f['airline']}\n\n"
        )

        buttons.append([{
            "text": f"Book Option {i} ✈️",
            "url": f["link"]
        }])

    send_message(chat_id, msg, buttons)

# -------- WEBHOOK ROUTE --------
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
            send_message(chat_id,
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
    return "✅ Skyscanner-style Bot Running", 200

# -------- START --------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
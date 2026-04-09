import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

RAPIDAPI_HOST = "kiwi-com-cheap-flights.p.rapidapi.com"
ORIGIN = "MNL"

app = Flask(__name__)

# Country fallback airports
COUNTRY_AIRPORTS = {
    "thailand": ["BKK", "HKT", "CNX"],
    "singapore": ["SIN"],
    "japan": ["NRT", "HND", "KIX"],
    "korea": ["ICN", "PUS"],
    "usa": ["JFK", "LAX", "SFO", "ORD", "MIA"],
    "united states": ["JFK", "LAX", "SFO", "ORD", "MIA"],
    "malaysia": ["KUL", "PEN"],
    "vietnam": ["SGN", "HAN", "DAD"],
    "china": ["PEK", "PVG", "CAN"],
    "hong kong": ["HKG"],
    "australia": ["SYD", "MEL", "BNE"]
}

# -------- TELEGRAM --------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


# -------- KIWI API --------
def get_iata_codes(location_name):
    url = f"https://{RAPIDAPI_HOST}/locations/query"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    params = {
        "term": location_name,
        "location_types": "airport,city",
        "limit": 5
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            return []

        data = res.json()
        return [loc["code"] for loc in data.get("locations", []) if "code" in loc]

    except:
        return []


def search_flight(dest_iata):
    url = f"https://{RAPIDAPI_HOST}/v2/search"

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    date_from = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    date_to = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")

    params = {
        "fly_from": ORIGIN,
        "fly_to": dest_iata,
        "date_from": date_from,
        "date_to": date_to,
        "curr": "PHP",
        "sort": "price",
        "limit": 3
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        if res.status_code != 200:
            return None, None

        flights = res.json().get("data", [])
        if flights:
            cheapest = min(flights, key=lambda x: x["price"])
            return cheapest["price"], cheapest["deep_link"]

        return None, None

    except:
        return None, None


# -------- PARALLEL SEARCH --------
def find_cheapest(iata_codes):
    results = []

    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(search_flight, code) for code in iata_codes[:3]]
        for f in futures:
            results.append(f.result())

    valid = [(p, l) for p, l in results if p]

    if not valid:
        return None, None

    return min(valid, key=lambda x: x[0])


# -------- WEBHOOK --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json

    message = data.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    if not text:
        return "OK"

    user_input = text.strip().lower()

    # Normalize aliases
    aliases = {
        "us": "usa",
        "america": "usa",
        "korea": "korea"
    }
    user_input = aliases.get(user_input, user_input)

    send_message(chat_id, f"✈️ Searching flights to *{text}*...")

    # Step 1: get IATA
    iata_codes = get_iata_codes(user_input)

    # Step 2: fallback
    if not iata_codes and user_input in COUNTRY_AIRPORTS:
        iata_codes = COUNTRY_AIRPORTS[user_input]

    if not iata_codes:
        send_message(chat_id, "❌ Could not find destination. Try a city or airport.")
        return "OK"

    # Step 3: find cheapest
    price, link = find_cheapest(iata_codes)

    if price:
        reply = (
            f"✈️ *Cheapest Flight Found!*\n\n"
            f"📍 Manila → {text}\n"
            f"💰 ₱{price:,}\n\n"
            f"🔗 [Book Here]({link})"
        )
    else:
        reply = f"❌ No flights found for Manila → {text}"

    send_message(chat_id, reply)

    return "OK"


# -------- RUN SERVER --------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
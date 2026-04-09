import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# -------- LOAD ENV --------
load_dotenv()
TOKEN = os.getenv("TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")
RAPIDAPI_HOST = os.getenv("RAPIDAPI_HOST", "kiwi-com-cheap-flights.p.rapidapi.com")
ORIGIN = "MNL"

if not TOKEN or not RAPIDAPI_KEY:
    raise Exception("TOKEN or RAPIDAPI_KEY not set in .env")

app = Flask(__name__)

# -------- COUNTRY FALLBACK AIRPORTS --------
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

# -------- TELEGRAM MESSAGE --------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    })


# -------- KIWI API --------
def get_iata_codes(location_name):
    """Get IATA codes from Kiwi API or fallback."""
    # First try Kiwi
    url = f"https://{RAPIDAPI_HOST}/locations/query"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {"term": location_name, "location_types": "airport,city", "limit": 5}

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        locations = res.json().get("locations", [])
        codes = [loc["code"] for loc in locations if "code" in loc]
        if codes:
            return codes
    except Exception:
        pass

    # Fallback to country airports
    return COUNTRY_AIRPORTS.get(location_name.lower(), [])


def search_flight(dest_iata):
    """Return the cheapest flight price and link to a destination airport."""
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
        "limit": 1
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        res.raise_for_status()
        flights = res.json().get("data", [])
        if flights:
            flight = flights[0]
            return flight.get("price"), flight.get("deep_link")
        return None, None
    except Exception:
        return None, None


def find_cheapest(iata_codes):
    """Search all IATA codes in parallel and return the cheapest flight."""
    results = []
    with ThreadPoolExecutor(max_workers=len(iata_codes)) as executor:
        futures = [executor.submit(search_flight, code) for code in iata_codes]
        for f in futures:
            results.append(f.result())

    valid = [(p, l) for p, l in results if p]
    if not valid:
        return None, None
    return min(valid, key=lambda x: x[0])


# -------- FLASK WEBHOOK --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    message = data.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    if not text or not chat_id:
        return "OK"

    user_input = text.strip().lower()
    # Aliases
    aliases = {"us": "usa", "america": "usa", "korea": "korea"}
    user_input = aliases.get(user_input, user_input)

    send_message(chat_id, f"✈️ Searching flights to *{text}*...")

    iata_codes = get_iata_codes(user_input)
    if not iata_codes:
        send_message(chat_id, f"❌ Could not find destination for '{text}'. Try a city or airport.")
        return "OK"

    price, link = find_cheapest(iata_codes)

    if price:
        reply = (
            f"✈️ *Cheapest Flight Found!*\n\n"
            f"📍 Manila → {text}\n"
            f"💰 ₱{price:,}\n\n"
            f"🔗 [Book Here]({link})"
        )
    else:
        reply = f"❌ No flights found for Manila → {text} in the next 30 days."

    send_message(chat_id, reply)
    return "OK"


# -------- RUN SERVER --------
if __name__ == "__main__":
    print("✅ Flask server running. TOKEN loaded correctly.")
    print("Send messages to your bot now!")
    app.run(host="0.0.0.0", port=5000)
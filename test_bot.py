import os
import requests
from flask import Flask, request
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

# -------- LOAD ENV --------
load_dotenv()
TOKEN = os.getenv("TOKEN")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

ORIGIN = "MNL"

app = Flask(__name__)

# -------- AIRPORT DATABASE --------
CITY_AIRPORTS = {
    "tokyo": ["NRT", "HND"],
    "osaka": ["KIX"],
    "seoul": ["ICN"],
    "bangkok": ["BKK"],
    "singapore": ["SIN"],
    "kuala lumpur": ["KUL"],
    "hong kong": ["HKG"],
    "taipei": ["TPE"],
    "dubai": ["DXB"],
    "los angeles": ["LAX"],
    "new york": ["JFK"],
}

COUNTRY_AIRPORTS = {
    "japan": ["NRT", "HND", "KIX"],
    "korea": ["ICN", "PUS"],
    "thailand": ["BKK", "HKT"],
    "usa": ["JFK", "LAX"],
    "australia": ["SYD", "MEL"],
}

# -------- TELEGRAM --------
def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={
        "chat_id": chat_id,
        "text": text
    })


# -------- GET IATA --------
def get_iata_codes(location_name):
    location_name = location_name.lower().strip()

    if location_name in CITY_AIRPORTS:
        return CITY_AIRPORTS[location_name]

    if location_name in COUNTRY_AIRPORTS:
        return COUNTRY_AIRPORTS[location_name]

    return []


# -------- SEARCH FLIGHT --------
def search_flight(dest_iata):
    url = "https://kiwi-com-cheap-flights.p.rapidapi.com/round-trip"

    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": "kiwi-com-cheap-flights.p.rapidapi.com"
    }

    params = {
        "source": ORIGIN,
        "destination": dest_iata,
        "currency": "PHP"
    }

    try:
        res = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"DEBUG API {dest_iata}: {res.status_code}")

        data = res.json()

        # ✅ CORRECT STRUCTURE
        itineraries = data.get("data", {}).get("returnItineraries", {}).get("itineraries", [])

        if not itineraries:
            return None

        # get first (cheapest usually)
        item = itineraries[0]

        price = int(float(item["price"]["amount"]))

        outbound = item["outbound"]["sectorSegments"][0]["segment"]
        airline = outbound["carrier"]["name"]

        return {
            "price": price,
            "iata": dest_iata,
            "airline": airline
        }

    except Exception as e:
        print("ERROR:", e)
        return None


# -------- FIND CHEAPEST --------
def find_cheapest(iata_codes):
    results = []

    with ThreadPoolExecutor(max_workers=len(iata_codes)) as executor:
        futures = [executor.submit(search_flight, code) for code in iata_codes]

        for f in futures:
            result = f.result()
            if result:
                results.append(result)

    if not results:
        return None

    return min(results, key=lambda x: x["price"])


# -------- WEBHOOK --------
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    data = request.json
    print("RAW DATA:", data)

    message = data.get("message", {})
    text = message.get("text")
    chat_id = message.get("chat", {}).get("id")

    if not text:
        return "OK"

    user_input = text.lower().strip()
    print("USER INPUT:", user_input)

    send_message(chat_id, f"✈️ Searching flights to {text}...")

    iata_codes = get_iata_codes(user_input)
    print("IATA CODES:", iata_codes)

    if not iata_codes:
        send_message(chat_id,
            "❌ Destination not supported.\n\nTry: Tokyo, Osaka, Singapore, Bangkok"
        )
        return "OK"

    result = find_cheapest(iata_codes)

    if result:
        reply = (
            f"✈️ Cheapest Flight Found!\n\n"
            f"📍 Manila → {text}\n"
            f"🛫 Airline: {result['airline']}\n"
            f"💰 ₱{result['price']:,}"
        )
    else:
        reply = f"❌ No flights found for Manila → {text}"

    send_message(chat_id, reply)

    return "OK"


# -------- RUN --------
if __name__ == "__main__":
    print("✅ Bot is running...")
    app.run(host="0.0.0.0", port=5000)
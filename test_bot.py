import os
import time
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
RAPIDAPI_KEY = os.getenv("RAPIDAPI_KEY")

RAPIDAPI_HOST = "kiwi-com-cheap-flights.p.rapidapi.com"
ORIGIN = "MNL"

# Predefined major airports for countries (fallback if user types a country)
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

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def get_iata_codes(location_name):
    """Get IATA codes from Kiwi Locations API"""
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
        response = requests.get(url, headers=headers, params=params).json()
        locations = response.get("locations", [])
        codes = [loc["code"] for loc in locations if "code" in loc]
        return codes
    except Exception as e:
        print("Kiwi Locations API error:", e)
        return []

def search_flight(dest_iata):
    """Search cheapest flight using Kiwi Search API"""
    url = f"https://{RAPIDAPI_HOST}/v2/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }

    # Date range: tomorrow to 1 month later
    date_from = (datetime.now() + timedelta(days=1)).strftime("%d/%m/%Y")
    date_to = (datetime.now() + timedelta(days=30)).strftime("%d/%m/%Y")

    params = {
        "fly_from": ORIGIN,
        "fly_to": dest_iata,
        "date_from": date_from,
        "date_to": date_to,
        "one_for_city": 1,
        "curr": "PHP",
        "sort": "price",
        "limit": 1
    }

    try:
        response = requests.get(url, headers=headers, params=params).json()
        flights = response.get("data", [])
        if flights:
            flight = flights[0]
            return flight.get("price"), flight.get("deep_link")
        return None, None
    except Exception as e:
        print("Kiwi Search API error:", e)
        return None, None

def handle_telegram_messages():
    last_update_id = 0
    print("🚀 Flight Bot running (Dynamic Kiwi version)")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url).json()

            for result in response.get("result", []):
                last_update_id = result["update_id"]
                message = result.get("message", {}).get("text")
                if not message:
                    continue

                user_input = message.strip().lower()
                send_message(f"✈️ Searching flights from Manila to '{message.strip()}'...")

                # Step 1: Try getting IATA codes directly from Kiwi
                iata_codes = get_iata_codes(user_input)

                # Step 2: If no codes found, check fallback country airports
                if not iata_codes and user_input in COUNTRY_AIRPORTS:
                    iata_codes = COUNTRY_AIRPORTS[user_input]

                if not iata_codes:
                    send_message(f"❌ Could not find any airport for '{message.strip()}'. Try a city or major airport.")
                    continue

                # Step 3: Search flights across all IATA codes and pick the cheapest
                cheapest_price = None
                cheapest_link = None
                for code in iata_codes:
                    price, link = search_flight(code)
                    if price:
                        if cheapest_price is None or price < cheapest_price:
                            cheapest_price = price
                            cheapest_link = link

                if cheapest_price and cheapest_link:
                    reply = (
                        f"✅ Cheapest flight found!\n\n"
                        f"📍 Manila → {message.strip()}\n"
                        f"💰 ₱{cheapest_price:,}\n"
                        f"🔗 {cheapest_link}"
                    )
                else:
                    reply = f"❌ No flights found for Manila → {message.strip()} in the next month."

                send_message(reply)

        except Exception as e:
            print("Bot loop error:", e)

        time.sleep(3)

if __name__ == "__main__":
    handle_telegram_messages()
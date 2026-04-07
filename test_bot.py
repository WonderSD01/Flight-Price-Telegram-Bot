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

# RapidAPI host
RAPIDAPI_HOST = "kiwi-com-provider.p.rapidapi.com"

# Manila IATA code
ORIGIN = "MNL"

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": text})

def get_iata_codes(city_name):
    """
    Call Kiwi Locations API to get IATA codes for a city/country
    Returns a list of IATA codes
    """
    url = f"https://{RAPIDAPI_HOST}/locations/query"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    params = {
        "term": city_name,
        "location_types": "airport,city",
        "limit": 5
    }
    try:
        response = requests.get(url, headers=headers, params=params).json()
        locations = response.get("locations", [])
        iata_codes = [loc["code"] for loc in locations if "code" in loc]
        return iata_codes
    except Exception as e:
        print("Kiwi Locations API error:", e)
        return []

def search_flight(dest_iata):
    """
    Search cheapest flight using Kiwi Search API
    """
    url = f"https://{RAPIDAPI_HOST}/v2/search"
    headers = {
        "X-RapidAPI-Key": RAPIDAPI_KEY,
        "X-RapidAPI-Host": RAPIDAPI_HOST
    }
    # Date range: tomorrow to 1 month
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
        data = response.get("data", [])
        if data:
            flight = data[0]
            price = flight.get("price")
            link = flight.get("deep_link")
            return price, link
        return None, None
    except Exception as e:
        print("Kiwi Search API error:", e)
        return None, None

def handle_telegram_messages():
    last_update_id = 0
    print("🚀 Flight Bot running (Dynamic RapidAPI Kiwi)")

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}"
            response = requests.get(url).json()

            for result in response.get("result", []):
                last_update_id = result["update_id"]
                message = result.get("message", {}).get("text")
                if not message:
                    continue

                city_name = message.strip()
                send_message(f"✈️ Searching flights from Manila to '{city_name}'...")

                # Get IATA codes dynamically
                iata_codes = get_iata_codes(city_name)
                if not iata_codes:
                    send_message(f"❌ Could not find airport for '{city_name}'. Try a major city or country.")
                    continue

                # Search flights for the first valid IATA code
                price, link = None, None
                for code in iata_codes:
                    price, link = search_flight(code)
                    if price and link:
                        break

                if price and link:
                    reply = f"✅ Cheapest flight found:\n📍 Manila → {city_name}\n💰 ₱{price:,}\n🔗 {link}"
                else:
                    reply = f"❌ No flights found for Manila → {city_name} in the next month."

                send_message(reply)

        except Exception as e:
            print("Bot loop error:", e)

        time.sleep(3)

if __name__ == "__main__":
    handle_telegram_messages()
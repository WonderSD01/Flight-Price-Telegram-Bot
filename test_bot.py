import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from webdriver_manager.chrome import ChromeDriverManager

# --- CONFIGURATION ---
TOKEN = "8774011337:AAEAIDg_5R204ToKBW0Tuu_tIUHlRd7QPb0"
CHAT_ID = "908651332"

def scrape_lowest_flight(destination):
    """The logic to open browser and find the cheapest price on the page"""
    chrome_options = Options()
    # chrome_options.add_argument("--headless") # Background mode
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    
    try:
        driver.get("https://www.google.com/flights")
        time.sleep(3)

        # Input Destination from user
        to_box = driver.find_element(By.CSS_SELECTOR, "input[placeholder='Where to?']")
        to_box.send_keys(destination)
        time.sleep(1)
        to_box.send_keys(Keys.ENTER)
        time.sleep(5) # Wait for all flights to load

        # Find ALL prices on the page
        price_elements = driver.find_elements(By.XPATH, "//span[contains(text(), '₱')]")
        all_prices = []

        for el in price_elements:
            raw_text = el.text.replace('₱', '').replace(',', '').strip()
            if raw_text.isdigit():
                all_prices.append(int(raw_text))

        if all_prices:
            lowest = min(all_prices) # Find the absolute lowest
            return lowest, driver.current_url
        return None, None

    finally:
        driver.quit()

def handle_telegram_messages():
    """Checks Telegram for new destination requests"""
    last_update_id = 0
    print("Bot is listening... Type a country name in Telegram!")

    while True:
        # Check for new messages
        url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={last_update_id + 1}"
        response = requests.get(url).json()

        for result in response.get("result", []):
            last_update_id = result["update_id"]
            user_message = result["message"]["text"]
            
            # Acknowledge the request
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": f"🔍 Searching for the cheapest flights to {user_message}..."})

            # Run the scraper
            price, link = scrape_lowest_flight(user_message)

            if price:
                reply = f"✈️ LOWEST PRICE FOUND!\n📍 To: {user_message}\n💰 Price: ₱{price}\n🔗 Link: {link}"
            else:
                reply = f"❌ Sorry, I couldn't find any flights to {user_message} right now."
            
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", 
                          data={"chat_id": CHAT_ID, "text": reply})

        time.sleep(3) # Don't spam the API

if __name__ == "__main__":
    handle_telegram_messages()
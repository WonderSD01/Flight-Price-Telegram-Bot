# Interactive Flight Price Telegram Bot
An automated Python system that listens for destinations via Telegram, scrapes real-time prices from Google Flights using Selenium, and alerts the user of the cheapest deal.

# Tech Stack
* **Language:** Python 3.13
* **Automation:** Selenium WebDriver
* **Messaging:** Telegram Bot API (Requests)
* **Environment:** ChromeDriverManager

# How it Works
1. User sends a country name to the Telegram Bot.
2. Python script detects the message and launches a headless browser.
3. Selenium extracts the absolute lowest price from the search results.
4. Bot replies to the user with the price and a direct booking link.

import requests
import os
from dotenv import load_dotenv
import time

load_dotenv()

CRYPTOCARE_API_KEY = os.getenv("CRYPTOCARE_API_KEY")

def get_latest_price(symbols, currency='USD'):
    """Fetches the latest price (same as before)"""
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={','.join(symbols)}&tsyms={currency}&api_key={CRYPTOCARE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CryptoCompare API: {e}")
        return None

def get_historical_daily_data(symbol, currency='USD', limit=30):
    """
    Fetches historical daily price data for a cryptocurrency from CryptoCompare API.

    Args:
        symbol (str): Cryptocurrency symbol (e.g., 'BTC').
        currency (str, optional): Currency to convert to. Defaults to 'USD'.
        limit (int, optional): Number of historical days to fetch. Defaults to 30.

    Returns:
        list: A list of dictionaries containing historical data, or None if error.
              Example: [{'time': 1674883200, 'open': 23000, 'high': 23500, 'low': 22800, 'close': 23200, 'volumefrom': ..., 'volumeto': ...}, ...]
              Returns None and prints an error message if API request fails.
    """
    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={symbol}&tsym={currency}&limit={limit}&api_key={CRYPTOCARE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        if data['Response'] == 'Success':
            return data['Data']['Data'] # Access the 'Data' array within 'Data'
        else:
            print(f"Error from CryptoCompare API: {data.get('Message', 'Unknown error')}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error fetching historical data from CryptoCompare API: {e}")
        return None


if __name__ == '__main__':
    # Example usage for historical data:
    crypto_symbol = 'BTC'
    historical_data = get_historical_daily_data(crypto_symbol)

    if historical_data:
        print(f"Historical Daily Data for {crypto_symbol} (Last 30 Days):")
        for day_data in historical_data:
            print(f"Date: {time.strftime('%Y-%m-%d', time.localtime(day_data['time']))}, Close Price: ${day_data['close']}")
    else:
        print(f"Failed to retrieve historical data for {crypto_symbol}.")
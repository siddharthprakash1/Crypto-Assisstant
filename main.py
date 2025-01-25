import time
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI  # Updated Gemini import!
from langchain.chains import LLMChain # Importing LLMChain
from langchain.prompts import ChatPromptTemplate # Importing ChatPromptTemplate


load_dotenv()

CRYPTO_COMPARE_API_KEY = os.getenv("CRYPTOCARE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)


# -------------------- Data Layer (CryptoCompare API) --------------------
print("--- Defining Data Layer Functions ---")

def get_latest_price(symbols, currency='USD'):
    print("Entering get_latest_price function")
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={','.join(symbols)}&tsyms={currency}&api_key={CRYPTO_COMPARE_API_KEY}"
    print(f"API Request URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        data = response.json()
        print("API Response Data:", data)  # Print API response
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CryptoCompare API: {e}")
        return None

# -------------------- Analysis Engine (Langchain & Gemini) --------------------
print("--- Defining Analysis Engine Functions ---")

def analyze_price_with_gemini(crypto_symbol, price):
    print("Entering analyze_price_with_gemini function")
    print(f"Analyzing symbol: {crypto_symbol}, price: {price}")

    try:
        print("Initializing Gemini LLM using ChatGoogleGenerativeAI...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=GEMINI_API_KEY,
            temperature=0.7  # You can adjust temperature
        )
        print("Gemini LLM initialized successfully.")

        # --- Define Prompt for Analysis ---
        analysis_template = """You are a cryptocurrency analyst providing concise insights on current crypto prices.

        Analyze the current price of {crypto_symbol} which is ${price} USD.

        Provide a brief, insightful analysis focusing on potential short-term trends or observations based solely on this price point. Be concise and informative.

        Format your response as a short paragraph."""

        analysis_prompt = ChatPromptTemplate.from_template(analysis_template)
        print("Analysis prompt created.")

        analysis_chain = LLMChain(llm=llm, prompt=analysis_prompt) # Initialize LLMChain
        print("Analysis LLMChain initialized.")

        print("Invoking analysis chain...")
        analysis_output = analysis_chain.invoke({"crypto_symbol": crypto_symbol, "price": price}) # Invoke chain with input
        analysis_text = analysis_output['text'] # Extract text from output
        print("Analysis chain invoked.")
        print("Gemini Analysis Result:\n", analysis_text)
        return analysis_text # Return the text analysis

    except Exception as e:
        error_message = f"Error during analysis with Gemini: {e}"
        print(error_message)
        return error_message

# -------------------- Alert System (Placeholder) --------------------
print("--- Defining Alert System Functions ---")

def check_price_alerts(prices):
    print("Entering check_price_alerts function")
    alerts = []
    # Add alert logic here based on price thresholds, etc.
    # Example (very basic):
    # if prices.get('BTC', {}).get('USD', 0) > 31000:
    #     alerts.append("BTC price above $31000!")
    print("Alert checks completed (placeholder logic). No alerts triggered yet.")
    return alerts

# -------------------- Portfolio Manager (Placeholder) --------------------
print("--- Defining Portfolio Manager Functions ---")

def track_portfolio(transactions):
    print("Entering track_portfolio function")
    portfolio_summary = {"holdings": {}, "performance": "N/A"} # Placeholder
    # Add portfolio tracking logic here
    print("Portfolio tracking completed (placeholder logic).")
    return portfolio_summary

def display_portfolio_summary(summary):
    print("Entering display_portfolio_summary function")
    print("\nPortfolio Summary:")
    print(f"Holdings: {summary.get('holdings')}")
    print(f"Performance: {summary.get('performance')}")
    print("Portfolio summary displayed.")


# -------------------- Main Application Logic --------------------
print("--- Defining Main Application Logic (main function) ---")

def main():
    print("Entering main function")
    crypto_symbols = ['BTC', 'ETH'] # Symbols to monitor
    transactions = [] # Placeholder for transaction data

    print("Crypto Trading Assistant Started!")

    while True: # Real-time monitoring loop (simplified for demonstration)
        print("\n--- Starting Monitoring Loop Iteration ---")
        prices = get_latest_price(crypto_symbols)

        if prices:
            print("\n--- Real-time Monitoring Data Received ---")
            for symbol, price_data in prices.items():
                if usd_price := price_data.get('USD'):
                    print(f"{symbol}: ${usd_price}")

                    # Analyze price with Gemini
                    print(f"Calling analyze_price_with_gemini for {symbol}...")
                    analysis = analyze_price_with_gemini(symbol, usd_price)
                    print(f"Gemini Analysis for {symbol}:\n{analysis}\n")
                else:
                    print(f"Price data for {symbol} in USD not found.")

            # Check for alerts
            print("Checking for alerts...")
            triggered_alerts = check_price_alerts(prices)
            if triggered_alerts:
                print("\nAlerts:")
                for alert in triggered_alerts:
                    print(f"- {alert}")
            else:
                print("No alerts triggered.")

            # Portfolio Management
            print("Updating portfolio...")
            portfolio_summary = track_portfolio(transactions)
            display_portfolio_summary(portfolio_summary)

        else:
            print("Failed to get crypto prices. Retrying in 30 seconds...")

        print("Sleeping for 30 seconds...")
        time.sleep(30) # Check every 30 seconds

if __name__ == "__main__":
    print("--- Script execution started ---")
    main()
    print("--- Script execution finished ---")
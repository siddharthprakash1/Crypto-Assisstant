from flask import Flask, render_template
import time
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_community.utilities import GoogleSerperAPIWrapper # Import Serper

app = Flask(__name__)

load_dotenv()
print("dotenv loaded. Checking environment variables...") # Debug print

CRYPTOCARE_API_KEY = os.getenv("CRYPTOCARE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY") # Load Serper API key

print(f"CRYPTOCARE_API_KEY from env: {CRYPTOCARE_API_KEY}") # Debug print
print(f"GEMINI_API_KEY from env: {GEMINI_API_KEY}") # Debug print
print(f"SERPER_API_KEY from env: {SERPER_API_KEY}") # Debug print

genai.configure(api_key=GEMINI_API_KEY)

# Initialize Serper API wrapper
print("Attempting to initialize GoogleSerperAPIWrapper...") # Debug print
serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY) # Initialize Serper API wrapper
print("GoogleSerperAPIWrapper initialized successfully.") # Debug print


# -------------------- Data Layer (CryptoCompare API) --------------------
print("--- Defining Data Layer Functions ---")

def get_latest_price(symbols, currency='USD'):
    print("Entering get_latest_price function")
    url = f"https://min-api.cryptocompare.com/data/pricemulti?fsyms={','.join(symbols)}&tsyms=USD&api_key={CRYPTO_COMPARE_API_KEY}"
    print(f"API Request URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print("API Response Data:", data)
        return data
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CryptoCompare API: {e}")
        return None

# -------------------- Analysis Engine (Langchain & Gemini) --------------------
print("--- Defining Analysis Engine Functions ---")

def analyze_price_with_gemini(crypto_symbol, price, serper_search): # Pass serper_search
    print("Entering analyze_price_with_gemini function")
    print(f"Analyzing symbol: {crypto_symbol}, price: {price}")

    try:
        print("Initializing Gemini LLM using ChatGoogleGenerativeAI...")
        llm = ChatGoogleGenerativeAI(
            model="gemini-pro",
            google_api_key=GEMINI_API_KEY,
            temperature=0.7
        )
        print("Gemini LLM initialized successfully.")

        # --- Define Prompt for Analysis with Sentiment Search ---
        analysis_template = """You are a cryptocurrency analyst providing concise insights on current crypto prices, incorporating sentiment from recent news.

        Current Price of {crypto_symbol}: ${price} USD.

        To understand market sentiment, perform a web search using the query: "recent news sentiment {crypto_symbol}".  Use the search results to gauge the current market sentiment around {crypto_symbol}.

        Based on the current price and the recent news sentiment, provide a brief, insightful analysis focusing on potential short-term trends or observations. Be concise and informative, and mention the sentiment if it's significantly positive or negative.

        Format your response as a short paragraph."""

        analysis_prompt = ChatPromptTemplate.from_template(analysis_template)
        print("Analysis prompt created.")

        analysis_chain = LLMChain(llm=llm, prompt=analysis_prompt)
        print("Analysis LLMChain initialized.")

        print("Performing web search for sentiment...")
        search_query = f"recent news sentiment {crypto_symbol}"
        sentiment_news = serper_search.run(search_query) # Use serper search
        print("Web search for sentiment completed.")
        print("Sentiment News Snippets:\n", sentiment_news[:500] + "...") # Preview first 500 chars

        print("Invoking analysis chain...")
        analysis_output = analysis_chain.invoke({"crypto_symbol": crypto_symbol, "price": price, "sentiment_news": sentiment_news}) # Pass sentiment news
        analysis_text = analysis_output['text']
        print("Analysis chain invoked.")
        print("Gemini Analysis Result:\n", analysis_text)
        return analysis_text

    except Exception as e:
        error_message = f"Error during analysis with Gemini: {e}"
        print(error_message)
        return error_message


# -------------------- Routes (Web Endpoints) --------------------
@app.route("/")
def index():
    crypto_symbols = ['BTC', 'ETH']
    prices = get_latest_price(crypto_symbols)
    analysis_results = {}

    if prices:
        for symbol, price_data in prices.items():
            if usd_price := price_data.get('USD'):
                analysis = analyze_price_with_gemini(symbol, usd_price, serper) # Pass serper here
                analysis_results[symbol] = analysis
            else:
                analysis_results[symbol] = "Price data in USD not found."
        else:
            analysis_results = {"error": "Failed to fetch crypto prices."}

    return render_template("index.html", prices=prices, analysis_results=analysis_results)

if __name__ == "__main__":
    app.run(debug=True) # Run Flask app in debug mode for development
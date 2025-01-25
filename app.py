# app.py - Full Code

from flask import Flask, render_template, jsonify, url_for
import time
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_community.utilities import GoogleSerperAPIWrapper
from cryptocompare_api import get_latest_price, get_historical_daily_data

app = Flask(__name__)

load_dotenv(dotenv_path=os.path.join(os.getcwd(), '.env'))
print("dotenv loaded. Checking environment variables...")

print("\n--- Environment Variables Loaded by dotenv ---")
for key, value in os.environ.items():
    if key.endswith("_API_KEY") or "API_KEY" in key:
        print(f"{key}={value}")
print("--- End of Environment Variables ---")

CRYPTOCARE_API_KEY = os.getenv("CRYPTOCARE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

print(f"CRYPTOCARE_API_KEY from env: {CRYPTOCARE_API_KEY}")
print(f"GEMINI_API_KEY from env: {GEMINI_API_KEY}")
print(f"SERPER_API_KEY from env: {SERPER_API_KEY}")

genai.configure(api_key=GEMINI_API_KEY)

print("Attempting to initialize GoogleSerperAPIWrapper...")
serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)
print("GoogleSerperAPIWrapper initialized successfully.")

def get_latest_price(symbols, currency='USD'):
    print("Entering get_latest_price function")
    url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={','.join(symbols)}&tsyms={currency}&api_key={CRYPTOCARE_API_KEY}"
    print(f"API Request URL: {url}")
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        print("API Response Data:", data)
        return data.get('RAW', {})
    except requests.exceptions.RequestException as e:
        print(f"Error fetching data from CryptoCompare API: {e}")
        return {}

def analyze_price_with_gemini(crypto_symbol, price, serper_search):
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

        analysis_template = """You are a cryptocurrency analyst providing concise insights and investment guidance on current crypto prices, incorporating sentiment from recent news.

        Current Price of {crypto_symbol}: ${price} USD.

        To understand market sentiment, perform a web search using the query: "recent news sentiment {crypto_symbol}". Use the search results to gauge the current market sentiment around {crypto_symbol}.

        Based on the current price and recent news sentiment:

        1. Provide a brief, insightful analysis focusing on potential short-term trends or observations. Be concise and informative, and mention the sentiment if it's significantly positive or negative.
        2. Recommend a potential investment amount in USD for a hypothetical investor with a moderate risk tolerance, considering the current price and sentiment.
        3. Suggest a stop-loss percentage (e.g., 5%, 10%) to mitigate potential downside risk.
        4. Indicate a suitable investment timeframe (short-term, medium-term, long-term) based on your analysis.
        5. Briefly describe the best investment plan or strategy based on your analysis.

        Format your response as a short paragraph for the analysis, then "News and Sentiment:" followed by the news snippets, and finally list the investment recommendations (amount, stop-loss, timeframe, plan) as bullet points."""

        analysis_prompt = ChatPromptTemplate.from_template(analysis_template)
        print("Analysis prompt created.")

        analysis_chain = LLMChain(llm=llm, prompt=analysis_prompt)
        print("Analysis LLMChain initialized.")

        print("Performing web search for sentiment...")
        search_query = f"recent news sentiment {crypto_symbol}"
        sentiment_news = serper_search.run(search_query)
        print("Web search for sentiment completed.")
        print("Sentiment News Snippets:\n", sentiment_news[:500] + "...")

        print("Invoking analysis chain...")
        analysis_output = analysis_chain.invoke({"crypto_symbol": crypto_symbol, "price": price, "sentiment_news": sentiment_news})
        analysis_text = analysis_output['text']
        print("Analysis chain invoked.")
        print("Gemini Analysis Result:\n", analysis_text)

        analysis_paragraph = ""
        recommendations_text = ""
        news_and_sentiment_text = ""

        parts = analysis_text.split("News and Sentiment:")
        if len(parts) > 1:
            analysis_paragraph = parts[0].strip()
            news_and_recommendation_parts = parts[1].strip().split("Investment Recommendations:")
            if len(news_and_recommendation_parts) > 1:
                news_and_sentiment_text = news_and_recommendation_parts[0].strip()
                recommendations_text = news_and_recommendation_parts[1].strip()
            else:
                news_and_sentiment_text = news_and_recommendation_parts[0].strip()
        else:
            analysis_paragraph = parts[0].strip()

        return {"analysis": analysis_paragraph, "recommendations": recommendations_text, "sentiment_news": news_and_sentiment_text}

    except Exception as e:
        error_message = f"Error during analysis with Gemini: {e}"
        print(error_message)
        return error_message

def get_crypto_news(serper):
    """Fetch general cryptocurrency news using Serper API"""
    try:
        search_query = "cryptocurrency market news latest developments past 24 hours"
        results = serper.run(search_query)
        
        articles = []
        for result in results.split('\n'):
            if result.strip():
                articles.append({
                    'title': result[:result.find(' - ')] if ' - ' in result else result,
                    'snippet': result[result.find(' - ') + 3:] if ' - ' in result else '',
                    'source': 'Crypto News',
                    'time': 'Recent'
                })
        
        return articles[:6]
    except Exception as e:
        print(f"Error fetching crypto news: {e}")
        return []

@app.route("/chart-data/<symbol>")
def chart_data(symbol):
    historical_data = get_historical_daily_data(symbol)
    print(f"Historical Data for {symbol}: {historical_data}")

    if historical_data:
        labels = [time.strftime('%Y-%m-%d', time.localtime(item['time'])) for item in historical_data]
        prices = [item['close'] for item in historical_data]

        chart_data_response = {
            'labels': labels[::-1],
            'datasets': [{
                'label': f'{symbol} Price (USD)',
                'data': prices[::-1],
                'borderColor': 'rgba(54, 162, 235, 1)',
                'backgroundColor': 'rgba(54, 162, 235, 0.1)',
                'borderWidth': 2,
                'tension': 0.4,
                'fill': 'origin' 
            }]
        }
        print(f"Chart Data for {symbol}: {chart_data_response}")
        return jsonify(chart_data_response)
    else:
        return jsonify({'error': 'Failed to fetch historical data'}), 500

@app.route("/")
def index():
    crypto_symbols = ['BTC', 'ETH']
    prices_full_data = get_latest_price(crypto_symbols)
    analysis_results = {}
    chart_urls = {}
    prices = {}
    
    current_time = time.strftime("%Y-%m-%d %H:%M:%S UTC")
    crypto_news = get_crypto_news(serper)

    if prices_full_data:
        for symbol in crypto_symbols:
            symbol_raw_data = prices_full_data.get(symbol, {}).get('USD', {})
            if symbol_raw_data:
                current_price = symbol_raw_data.get('PRICE')
                high_24h = symbol_raw_data.get('HIGH24HOUR')
                low_24h = symbol_raw_data.get('LOW24HOUR')

                prices[symbol] = {
                    'USD': current_price,
                    'HIGH24HOUR': high_24h,
                    'LOW24HOUR': low_24h
                }

                if current_price is not None:
                    gemini_response = analyze_price_with_gemini(symbol, current_price, serper)
                    analysis_results[symbol] = gemini_response
                    chart_urls[symbol] = url_for('chart_data', symbol=symbol)
                else:
                    analysis_results[symbol] = {"error": "Current price data not found."}
                    chart_urls[symbol] = None
            else:
                prices[symbol] = {'USD': None, 'HIGH24HOUR': None, 'LOW24HOUR': None}
                analysis_results[symbol] = {"error": "Price data in USD not found."}
                chart_urls[symbol] = None
    else:
        analysis_results = {"error": "Failed to fetch crypto prices."}
        chart_urls = {symbol: None for symbol in crypto_symbols}
        prices = {symbol: {'USD': None, 'HIGH24HOUR': None, 'LOW24HOUR': None} for symbol in crypto_symbols}

    return render_template(
        "index.html",
        prices=prices,
        analysis_results=analysis_results,
        chart_urls=chart_urls,
        current_time=current_time,
        crypto_news=crypto_news
    )

if __name__ == "__main__":
    app.run(debug=True)
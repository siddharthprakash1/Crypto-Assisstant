from flask import Flask, render_template, jsonify, request
import time
import json
from datetime import datetime
import requests
import os
from dotenv import load_dotenv
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains import LLMChain
from langchain.prompts import ChatPromptTemplate
from langchain_community.utilities import GoogleSerperAPIWrapper
from functools import lru_cache
from time import sleep

app = Flask(__name__)

# Load environment variables
load_dotenv()
CRYPTOCARE_API_KEY = os.getenv("CRYPTOCARE_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
SERPER_API_KEY = os.getenv("SERPER_API_KEY")

# Initialize APIs
genai.configure(api_key=GEMINI_API_KEY)
serper = GoogleSerperAPIWrapper(serper_api_key=SERPER_API_KEY)

@lru_cache(maxsize=128)
def get_cached_price(symbol, timestamp):
    return get_crypto_price(symbol)

@lru_cache(maxsize=128)
def get_cached_historical(symbol, timestamp):
    return get_historical_data(symbol)

@lru_cache(maxsize=128)
def get_cached_news(symbol, category, timestamp):
    return get_crypto_news(symbol, category)

def get_crypto_price(symbol):
    url = f"https://min-api.cryptocompare.com/data/pricemultifull?fsyms={symbol}&tsyms=USD&api_key={CRYPTOCARE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('RAW', {}).get(symbol, {}).get('USD', {})
    except Exception as e:
        print(f"Error fetching price: {e}")
        return {}

def get_historical_data(symbol, limit=30):
    url = f"https://min-api.cryptocompare.com/data/v2/histoday?fsym={symbol}&tsym=USD&limit={limit}&api_key={CRYPTOCARE_API_KEY}"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return data.get('Data', {}).get('Data', [])
    except Exception as e:
        print(f"Error fetching historical data: {e}")
        return []


def analyze_with_gemini(symbol, price_data, max_retries=3):
    for attempt in range(max_retries):
        try:
            llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=GEMINI_API_KEY,
                temperature=0.7
            )

            template = """You are an expert cryptocurrency analyst. Analyze the following data for {symbol}:
            Current Price: ${price}
            24h High: ${high}
            24h Low: ${low}

            Return a detailed analysis in this exact JSON format:
            {{
                "market_points": [
                    "Detailed price trend: {symbol} has moved [up/down] by X% in the last 24h, currently at ${price}. This movement indicates...",
                    "Volume analysis: Trading volume shows [increasing/decreasing] momentum, suggesting...",
                    "Technical indicators: RSI/MACD/Moving Averages are showing [bullish/bearish] signals because..."
                ],
                "outlook_points": [
                    "Price target: Expect movement towards $X in the short term based on...",
                    "Key levels: Major resistance at [price levels] and support at [price levels] based on recent trading patterns",
                    "Trading strategy: Consider [specific action] at current levels because..."
                ],
                "support": {low},
                "resistance": {high}
            }}

            Make each point specific, data-driven, and actionable. Include actual price levels and percentages."""

            prompt = ChatPromptTemplate.from_template(template)
            chain = LLMChain(llm=llm, prompt=prompt)

            analysis = chain.invoke({
                "symbol": symbol,
                "price": "{:,.2f}".format(price_data.get('PRICE', 0)),
                "high": price_data.get('HIGH24HOUR', 0),
                "low": price_data.get('LOW24HOUR', 0)
            })

            try:
                response_text = analysis.get('text', '').strip()
                if not response_text.startswith('{'): 
                    response_text = response_text[response_text.find('{'):]
                if not response_text.endswith('}'): 
                    response_text = response_text[:response_text.rfind('}')+1]
                    
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                print(f"JSON parsing error: {e}")
                return generate_fallback_analysis(symbol, price_data)

        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 2
                print(f"Rate limit hit, retrying in {sleep_time} seconds...")
                sleep(sleep_time)
                continue
            print(f"Analysis error: {e}")
            return generate_fallback_analysis(symbol, price_data)

def generate_fallback_analysis(symbol, price_data):
    """Generate fallback analysis when main analysis fails"""
    return {
        "market_points": [
            f"{symbol} is currently trading at ${price_data.get('PRICE', 0):,.2f}",
            "Analysis temporarily unavailable",
            "Please refresh for updated analysis"
        ],
        "outlook_points": [
            "Short-term outlook pending",
            "Support and resistance levels being calculated",
            "Try again in a few moments"
        ],
        "support": price_data.get('LOW24HOUR', 0),
        "resistance": price_data.get('HIGH24HOUR', 0)
    }



def get_crypto_news(symbol, category='market', max_retries=3):
    for attempt in range(max_retries):
        try:
            queries = {
                'market': f"{symbol} cryptocurrency price market analysis news last 24 hours",
                'development': f"{symbol} blockchain development updates technical news",
                'regulatory': f"{symbol} cryptocurrency regulation compliance news"
            }
            
            search_results = serper.run(queries.get(category, queries['market']))
            llm = ChatGoogleGenerativeAI(
                model="gemini-pro",
                google_api_key=GEMINI_API_KEY,
                temperature=0.3
            )

            news_items = []
            for result in search_results.split('\n')[:6]:
                if not result.strip():
                    continue
                    
                parts = result.split(' - ', 1)
                title = parts[0].strip()
                snippet = parts[1] if len(parts) > 1 else ''
                
                source_parts = snippet.split(' | ')
                source = source_parts[0] if len(source_parts) > 1 else 'News Source'
                
                try:
                    sentiment_prompt = f"Analyze the sentiment of this crypto news headline: '{title}'. Respond with ONLY one word: positive, negative, or neutral"
                    sentiment = llm.predict(sentiment_prompt).lower().strip()
                except Exception:
                    sentiment = "neutral"
                    
                news_items.append({
                    'title': title,
                    'snippet': snippet,
                    'source': source,
                    'time': 'Recent',
                    'sentiment': sentiment
                })
            
            return news_items
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                sleep_time = (attempt + 1) * 2
                print(f"Rate limit hit, retrying in {sleep_time} seconds...")
                sleep(sleep_time)
                continue
            print(f"News fetching error: {e}")
            return []

@app.route('/api/chart/<symbol>')
def get_chart_data(symbol):
    current_timestamp = int(time.time()) // 300 * 300
    historical_data = get_cached_historical(symbol, current_timestamp)
    
    if historical_data:
        chart_data = {
            'labels': [datetime.fromtimestamp(item['time']).strftime('%Y-%m-%d') 
                      for item in historical_data],
            'prices': [item['close'] for item in historical_data]
        }
        return jsonify(chart_data)
    return jsonify({'error': 'No data available'})

@app.route('/')
def index():
    selected_coin = request.args.get('coin', 'BTC')
    current_category = request.args.get('category', 'market')
    
    current_timestamp = int(time.time()) // 300 * 300
    price_data = get_cached_price(selected_coin, current_timestamp)
    
    if price_data:
        analysis = analyze_with_gemini(selected_coin, price_data)
    else:
        analysis = {
            "market_points": ["Price data unavailable"],
            "outlook_points": ["Analysis unavailable"],
            "support": 0,
            "resistance": 0
        }
    
    crypto_news = get_cached_news(selected_coin, current_category, current_timestamp)

    return render_template('index.html',
                         selected_coin=selected_coin,
                         current_category=current_category,
                         prices={selected_coin: price_data},
                         analysis_results={selected_coin: analysis},
                         crypto_news=crypto_news,
                         current_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC"))

if __name__ == '__main__':
    app.run(debug=True)
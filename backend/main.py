from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import random
import numpy as np
import urllib.parse
import urllib.request
import json
import os

# Import our custom modules
from matcher import evaluate_matches
from predictor import get_predictions

# Helper function to load local .env variables
def load_env():
    env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    try:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip().strip('"').strip("'")
                    except ValueError:
                        continue

load_env()

app = Flask(__name__)
# Enable CORS for frontend cross-origin requests
CORS(app)

# Real product page URLs for main demonstration items
REAL_PRODUCT_URLS = {
    "HP 15s Intel Core i3 Laptop (8GB/512GB)": {
        "Amazon India": "https://www.amazon.in/dp/B0CY5MSYQ8",
        "Flipkart": "https://www.flipkart.com/hp-15s-intel-core-i3-12th-gen-1215u-8-gb-512-gb-ssd-windows-11-home-15s-fy5007tu-thin-light-laptop/p/itm7e74cb2e6ebbf",
        "Croma": "https://www.croma.com/hp-15s-fy5007tu-intel-core-i3-12th-gen-15-6-inch-8gb-512gb-windows-11-home-intel-uhd-graphics-full-hd-display-natural-silver-9p3f2pa-/p/305282",
        "Reliance Digital": "https://www.reliancedigital.in/hp-15s-fy5007tu-intel-core-i3-12th-gen-15-6-inch-8gb-512gb-windows-11-home-intel-uhd-graphics-full-hd-display-natural-silver-9p3f2pa-/p/494352136"
    },
    "Lenovo IdeaPad Slim 3 Core i3 Laptop (8GB/512GB)": {
        "Amazon India": "https://www.amazon.in/dp/B0C3MB4ZJ5",
        "Flipkart": "https://www.flipkart.com/lenovo-ideapad-slim-3-intel-core-i3-12th-gen-1215u-8-gb-512-gb-ssd-windows-11-home-15iau7-thin-light-laptop/p/itm50682fa0fa1e5",
        "Croma": "https://www.croma.com/lenovo-ideapad-slim-3-15iau7-intel-core-i3-12th-gen-15-inch-8gb-512gb-windows-11-home-intel-uhd-graphics-fhd-display-arctic-grey-82rk00w2in-/p/304381"
    },
    "Dell Inspiron 3530 Core i3 Laptop (8GB/512GB)": {
        "Amazon India": "https://www.amazon.in/dp/B0D5D6T7MD",
        "Flipkart": "https://www.flipkart.com/dell-inspiron-3530-intel-core-i3-13th-gen-1305u-8-gb-512-gb-ssd-windows-11-home-inspiron-3530-thin-light-laptop/p/itm217ab22ba48a6"
    },
    "Apple iPhone 15 Pro Max (256GB)": {
        "Amazon India": "https://www.amazon.in/dp/B0CHX1W1XY",
        "Flipkart": "https://www.flipkart.com/apple-iphone-15-pro-max-natural-titanium-256-gb/p/itm9d623ab7d2d2c",
        "Croma": "https://www.croma.com/apple-iphone-15-pro-max-256gb-natural-titanium-/p/300654"
    },
    "Sony WH-1000XM4 Noise Canceling Headphones": {
        "Amazon India": "https://www.amazon.in/dp/B08C5FMFC2",
        "Flipkart": "https://www.flipkart.com/sony-wh-1000xm4-industry-leading-active-noise-cancellation-anc-bluetooth-headset/p/itm5b0bc9c4e2db9",
        "Croma": "https://www.croma.com/sony-wh-1000xm4-over-ear-active-noise-cancellation-wireless-headphone-with-mic-black-/p/228830"
    }
}

def get_product_url(product_name: str, store_name: str, query: str) -> str:
    # 1. Check if we have a hardcoded direct product URL
    if product_name in REAL_PRODUCT_URLS and store_name in REAL_PRODUCT_URLS[product_name]:
        return REAL_PRODUCT_URLS[product_name][store_name]
        
    # 2. Fallback: generate search results URL for this store
    encoded_query = urllib.parse.quote(query)
    if store_name == "Amazon India":
        return f"https://www.amazon.in/s?k={encoded_query}"
    elif store_name == "Flipkart":
        return f"https://www.flipkart.com/search?q={encoded_query}"
    elif store_name == "Croma":
        return f"https://www.croma.com/search/?text={encoded_query}"
    elif store_name == "Reliance Digital":
        return f"https://www.reliancedigital.in/search?q={encoded_query}"
    elif store_name == "Tata CLiQ":
        return f"https://www.tatacliq.com/search/?text={encoded_query}"
    elif store_name == "Vijay Sales":
        return f"https://www.vijaysales.com/search/{encoded_query}"
    elif store_name == "JioMart":
        return f"https://www.jiomart.com/search/{encoded_query}"
    elif store_name == "Snapdeal":
        return f"https://www.snapdeal.com/search?keyword={encoded_query}"
    elif store_name == "ShopClues":
        return f"https://www.shopclues.com/search?q={encoded_query}"
    elif store_name == "Meesho":
        return f"https://www.meesho.com/search?q={encoded_query}"
    else:
        return "https://www.google.com"

# Dictionary of preset categories & base prices to make predictions look authentic
PRODUCTS_DB = {
    "iphone 15 pro max": {"name": "Apple iPhone 15 Pro Max (256GB)", "price": 159900.00},
    "iphone 15": {"name": "Apple iPhone 15 (128GB)", "price": 79900.00},
    "playstation 5": {"name": "Sony PlayStation 5 Console Slim", "price": 54900.00},
    "ps5 pro": {"name": "Sony PlayStation 5 Pro Console", "price": 84900.00},
    "xbox series x": {"name": "Microsoft Xbox Series X (1TB)", "price": 54900.00},
    "nintendo switch": {"name": "Nintendo Switch OLED Model", "price": 29900.00},
    "sony wh-1000xm4": {"name": "Sony WH-1000XM4 Noise Canceling Headphones", "price": 22900.00},
    "sony wh-1000xm5": {"name": "Sony WH-1000XM5 Noise Canceling Headphones", "price": 29900.00},
    "airpods pro 2": {"name": "Apple AirPods Pro (2nd Generation)", "price": 24900.00},
    "geforce rtx 4080": {"name": "NVIDIA GeForce RTX 4080 Graphics Card", "price": 119900.00},
    "macbook air m3": {"name": "Apple MacBook Air 13.6\" M3 (8GB/256GB)", "price": 114900.00},
    "ipad pro m4": {"name": "Apple iPad Pro 11\" M4 (256GB Wi-Fi)", "price": 99900.00},
    "steam deck": {"name": "Valve Steam Deck OLED (512GB)", "price": 49900.00},
    "rog ally": {"name": "ASUS ROG Ally Handheld Gaming PC", "price": 59900.00},
    "bose quietcomfort": {"name": "Bose QuietComfort Wireless Headphones", "price": 29900.00}
}

STORES = [
    {"name": "Amazon India", "suffix": "- Prime Delivery - Free Shipping"},
    {"name": "Flipkart", "suffix": "- Assured Seller - Fast Delivery"},
    {"name": "Croma", "suffix": "- Tata Enterprise - Store Pickup Available"},
    {"name": "Reliance Digital", "suffix": "- Reliance ResQ Warranty - Ready Stock"},
    {"name": "Tata CLiQ", "suffix": "- Certified Original - Brand Warranty"},
    {"name": "Vijay Sales", "suffix": "- Festive Discount Offer - 1 Year Warranty"},
    {"name": "JioMart", "suffix": "- Reliance Grocer & Tech - Quick Home Delivery"},
    {"name": "Snapdeal", "suffix": "- Budget Deal - Cash on Delivery Available"},
    {"name": "ShopClues", "suffix": "- Wholesale Special Bargain - Value Buy"},
    {"name": "Meesho", "suffix": "- Manufacturer Direct - Lowest Price Offer"}
]

def search_products_db(query: str) -> tuple:
    """
    Looks up a query in the preset database. If not found, uses
    regex keywords or a hash of the query name to create a stable base price.
    """
    clean_query = query.lower().strip()
    
    # Direct match check
    for db_key, data in PRODUCTS_DB.items():
        if db_key in clean_query or clean_query in db_key:
            return data["name"], data["price"]
            
    # Fuzzy keyword check
    if "iphone" in clean_query:
        return "Apple iPhone 15 Pro", 99900.00
    elif "playstation" in clean_query or "ps5" in clean_query:
        return "Sony PlayStation 5 Console", 54900.00
    elif "xbox" in clean_query:
        return "Microsoft Xbox Series X Console", 54900.00
    elif "switch" in clean_query:
        return "Nintendo Switch OLED Model", 29900.00
    elif "airpods" in clean_query:
        return "Apple AirPods Pro 2", 24900.00
    elif "headphone" in clean_query or "sony" in clean_query:
        return "Sony WH-1000XM4 Noise Canceling Headphones", 22900.00
    elif "rtx" in clean_query or "gpu" in clean_query:
        return "NVIDIA GeForce RTX 4070 Graphics Card", 59900.00
    elif "macbook" in clean_query:
        return "Apple MacBook Air 13\" Laptop", 114900.00
    elif "hp" in clean_query:
        return "HP 15s Intel Core i3 Laptop (8GB/512GB)", 38900.00
    elif "lenovo" in clean_query:
        return "Lenovo IdeaPad Slim 3 Core i3 Laptop (8GB/512GB)", 36900.00
    elif "dell" in clean_query:
        return "Dell Inspiron 3530 Core i3 Laptop (8GB/512GB)", 39900.00
    elif "laptop" in clean_query or "i3" in clean_query:
        return "HP 15s Intel Core i3 Laptop (8GB/512GB)", 38900.00
    elif "tv" in clean_query or "television" in clean_query:
        return "OnePlus Y Series 43\" Full HD LED Smart TV", 27999.00
    elif "watch" in clean_query or "smartwatch" in clean_query:
        return "Samsung Galaxy Watch 6 LTE (44mm)", 19999.00
    
    # Generate stable fallback price based on search string (scales between ₹8,000 and ₹53,000)
    hash_val = sum(ord(c) for c in query)
    base_price = round(8000.0 + ((hash_val * 73) % 45000), 2)
    # Format name nicely
    title_words = [w.capitalize() for w in clean_query.split()]
    formatted_name = " ".join(title_words)
    if not formatted_name:
        formatted_name = "Unknown Product"
    return formatted_name, base_price

def fetch_serpapi_shopping_results(query: str) -> list:
    """
    Fetches real shopping results from SerpApi for India region.
    Returns a list of products mapping site, title, base_price, and url.
    """
    api_key = os.environ.get("SERPAPI_KEY", "")
    encoded_query = urllib.parse.quote(query)
    url = f"https://serpapi.com/search.json?engine=google_shopping&q={encoded_query}&google_domain=google.co.in&gl=in&hl=en&api_key={api_key}"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            
        shopping_results = res_data.get("shopping_results", [])
        if not shopping_results:
            print("SerpApi returned no shopping results.")
            return []
            
        product_pool = []
        for item in shopping_results:
            title = item.get("title")
            store = item.get("source", "Google Shopping")
            
            # SerpApi extracted_price is a float if present
            price = item.get("extracted_price")
            if price is None:
                # Try parsing it from the price string
                raw_price = item.get("price", "0")
                try:
                    price = float(''.join(c for c in raw_price if c.isdigit() or c == '.'))
                except ValueError:
                    price = 0.0
            
            link = item.get("product_link") or item.get("link") or "https://google.com"
            
            product_pool.append({
                "site": store,
                "title": title,
                "base_price": price,
                "url": link
            })
            
        print(f"Successfully fetched {len(product_pool)} real results from SerpApi.")
        return product_pool
    except Exception as e:
        print(f"SerpApi fetch failed or timed out: {e}")
        return []

@app.route("/api/search", methods=["GET", "POST"])
def search_product():
    # Retrieve query
    if request.method == "POST":
        data = request.get_json() or {}
        query = data.get("query", "")
    else:
        query = request.args.get("query", "")
        
    if not query:
        return jsonify({"error": "No query provided"}), 400
        
    # 1. Resolve product base price and title (used for simulation and fallback metadata)
    resolved_title, base_price = search_products_db(query)
    
    # 2. Try fetching real deals using SerpApi
    product_pool = fetch_serpapi_shopping_results(query)
    used_fallback = False
    
    if not product_pool:
        # Fallback to simulation
        used_fallback = True
        print("Using simulated fallback product pool.")
        
        # Seed random based on product name for consistency
        seed_val = sum(ord(c) for c in query) % 5000
        random.seed(seed_val)
        
        for i, store in enumerate(STORES):
            # Create different listings. Occasionally mismatch some titles to test fuzzy matching.
            is_mismatch = (i == 4 and len(query) > 5) or (i == 8 and len(query) > 10)
            
            if is_mismatch:
                title = f"Alternative Accessory for {resolved_title} Setup"
                price_mult = 0.15  # cheap accessory price
            else:
                title = f"{resolved_title} {store['suffix']}"
                # Stores have slightly different price baselines (+- 5%)
                price_mult = 1.0 + random.uniform(-0.05, 0.05)
                
            store_price = round(base_price * price_mult, 2)
            url = get_product_url(resolved_title, store["name"], query)
            product_pool.append({
                "site": store["name"],
                "title": title,
                "base_price": store_price,
                "url": url
            })
            
    # 3. Evaluate matching scores using matcher.py
    match_logs = evaluate_matches(query, product_pool)
    
    # Find the top matched item (excluding mismatches if possible)
    valid_matches = [m for m in match_logs if m["is_matched"]]
    
    if valid_matches:
        # Use the average price of valid matches as current price, or the top match price
        top_match = valid_matches[0]
        actual_price = top_match["base_price"]
        
        # If we got real data from SerpApi, make the resolved title match the exact product title
        if not used_fallback:
            resolved_title = top_match["original_title"]
    else:
        # Fallback to the first match
        top_match = match_logs[0]
        actual_price = top_match["base_price"]
        
    # 4. Generate Machine Learning Predictions using predictor.py
    prediction_results = get_predictions(resolved_title, actual_price)
    
    # 5. Build final response
    response_data = {
        "success": True,
        "query": query,
        "resolved_title": resolved_title,
        "current_price": actual_price,
        "recommendation": prediction_results["recommendation"],
        "reason": prediction_results["reason"],
        "prob_drop_10": prediction_results["prob_drop_10"],
        "prob_drop_20": prediction_results["prob_drop_20"],
        "predicted_low": prediction_results["predicted_low"],
        "days_to_low": prediction_results["days_to_low"],
        "potential_savings_pct": prediction_results["potential_savings_pct"],
        "scan_logs": match_logs,
        "history": prediction_results["history"],
        "forecast": prediction_results["forecast"],
        "used_fallback": used_fallback
    }
    
    return jsonify(response_data)

@app.route("/api/health", methods=["GET"])
def health_check():
    return jsonify({"status": "healthy", "service": "dealpulse-backend"})

if __name__ == "__main__":
    print("Starting DealPulse Backend Server...")
    print("Server running at http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=True)

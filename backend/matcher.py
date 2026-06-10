import re

# Try to import rapidfuzz for fast similarity computations. Fallback to difflib if not available.
try:
    from rapidfuzz import fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    from difflib import SequenceMatcher
    USE_RAPIDFUZZ = False

def normalize_string(text: str) -> str:
    """
    Cleans and normalizes product strings for more accurate matching.
    Converts to lowercase, removes punctuation/special characters, and cleans whitespace.
    """
    if not text:
        return ""
    text = text.lower()
    # Remove punctuation like hyphens, slashes, commas, parentheses
    text = re.sub(r'[^\w\s]', ' ', text)
    # Collapse multiple spaces into one and strip
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def check_accessory_mismatch(norm_query: str, norm_target: str) -> bool:
    """
    Detects if there is an accessory mismatch between normalized query and target.
    Returns True if one contains an accessory term but the other does not, or
    if they contain different accessory terms with no overlap.
    """
    words_query = set(norm_query.split())
    words_target = set(norm_target.split())
    
    # Common accessory indicators (and their plural forms)
    ACCESSORY_KEYWORDS = {
        'case', 'cases', 'cover', 'covers', 'guard', 'guards', 'tempered', 'glass', 
        'pouch', 'pouches', 'bag', 'bags', 'sleeve', 'sleeves', 'adapter', 'adapters', 
        'charger', 'chargers', 'cable', 'cables', 'stand', 'stands', 'accessory', 'accessories', 
        'strap', 'straps', 'protector', 'protectors', 'holder', 'holders', 'mount', 'mounts', 
        'skin', 'skins', 'film', 'films', 'sticker', 'stickers', 'keychain', 'keychains'
    }
    
    query_acc = words_query.intersection(ACCESSORY_KEYWORDS)
    target_acc = words_target.intersection(ACCESSORY_KEYWORDS)
    
    # 1. Query has no accessory words, but target does (e.g. searching "iphone 15" matches "iphone 15 case")
    if not query_acc and target_acc:
        return True
        
    # 2. Query has accessory words, but target does not (e.g. searching "iphone 15 case" matches "iphone 15")
    if query_acc and not target_acc:
        return True
        
    # 3. Both have accessory words, but they do not overlap (e.g. searching "iphone 15 case" matches "iphone 15 charger")
    if query_acc and target_acc and not query_acc.intersection(target_acc):
        return True
        
    return False

def calculate_similarity(query: str, target: str) -> float:
    """
    Computes a match percentage score (0.0 to 100.0) between query and target strings.
    Utilizes token-subset matching so query keywords contained in longer titles match highly.
    Penalizes accessory mismatches to prevent e.g. cases matching phone searches.
    """
    norm_query = normalize_string(query)
    norm_target = normalize_string(target)
    
    if not norm_query or not norm_target:
        return 0.0
        
    # Penalize accessory mismatches
    if check_accessory_mismatch(norm_query, norm_target):
        return 15.0
        
    if USE_RAPIDFUZZ:
        # token_set_ratio is perfect for subset matching ("hp i3 laptop" in "HP 15s Intel Core i3 Laptop...")
        return float(fuzz.token_set_ratio(norm_query, norm_target))
    else:
        # Fallback to custom token-set fuzzy calculation using difflib SequenceMatcher
        from difflib import SequenceMatcher
        words_query = norm_query.split()
        words_target = norm_target.split()
        
        if not words_query:
            return 0.0
            
        matches = []
        for q_word in words_query:
            best_match = 0.0
            for t_word in words_target:
                if q_word == t_word:
                    best_match = 100.0
                    break
                ratio = SequenceMatcher(None, q_word, t_word).ratio() * 100.0
                if ratio > best_match:
                    best_match = ratio
            matches.append(best_match)
            
        return sum(matches) / len(matches) if matches else 0.0

def evaluate_matches(query: str, product_pool: list, threshold: float = 40.0) -> list:
    """
    Processes a list of potential product listings from various stores,
    calculates match percentage, and sorts by highest match score.
    """
    matched_results = []
    
    for item in product_pool:
        # Calculate similarity against both full title and a cleaned title
        score = calculate_similarity(query, item["title"])
        
        # Consider a match "valid" if it exceeds our threshold
        is_matched = score >= threshold
        
        # We classify high similarity (>= 75%) as a "High Match", middle as "Partial Match", rest "Unmatched"
        if score >= 75.0:
            confidence = "High"
        elif score >= 55.0:
            confidence = "Medium"
        elif score >= 40.0:
            confidence = "Low"
        else:
            confidence = "None"
            
        matched_results.append({
            "site": item["site"],
            "original_title": item["title"],
            "base_price": item["base_price"],
            "url": item.get("url", "#"),
            "match_score": round(score, 1),
            "confidence": confidence,
            "is_matched": is_matched
        })
        
    # Sort results by match score in descending order
    matched_results.sort(key=lambda x: x["match_score"], reverse=True)
    return matched_results

# Simple self-test code block
if __name__ == "__main__":
    print(f"Fuzzy Matching Library in use: {'RapidFuzz' if USE_RAPIDFUZZ else 'Difflib (Standard Library)'}")
    test_query = "Sony WH-1000XM4 Noise Canceling Headphones"
    test_items = [
        {"title": "Sony WH1000XM4/B Black Over-Ear Headphones", "site": "Amazon", "base_price": 348.00},
        {"title": "Sony WH-1000XM4 Wireless Noise-Cancelling Headphones", "site": "Best Buy", "base_price": 349.99},
        {"title": "Sony WH-1000XM5 Wireless Headphones (Silver)", "site": "eBay", "base_price": 398.00},
        {"title": "Samsung Galaxy Buds Pro 2 Wireless Earbuds", "site": "Walmart", "base_price": 179.99}
    ]
    
    results = evaluate_matches(test_query, test_items)
    for r in results:
        print(f"[{r['site']}] Score: {r['match_score']}% ({r['confidence']} Match) -> {r['original_title']}")

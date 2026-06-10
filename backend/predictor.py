import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier

def generate_historical_prices(product_name: str, base_price: float, num_days: int = 90) -> pd.DataFrame:
    """
    Generates realistic historical price data for a product.
    Includes noise, weekly cycles, overall downward trend, and periodic sales.
    """
    # Seed based on product name for deterministic behavior per product
    seed_val = sum(ord(c) for c in product_name) % 10000
    np.random.seed(seed_val)
    
    start_date = datetime.now() - timedelta(days=num_days)
    dates = [start_date + timedelta(days=i) for i in range(num_days)]
    
    prices = []
    current_price = base_price
    
    # Establish promotional frequency (e.g. sale every 14 to 20 days)
    promo_interval = np.random.randint(12, 22)
    last_promo_day = -promo_interval
    
    for day in range(num_days):
        # 1. Base trend (gradual depreciation over time)
        trend = -0.0003 * day * base_price
        
        # 2. Weekly cycle (prices slightly lower on weekends)
        weekday = dates[day].weekday()
        cycle = 0.0
        if weekday >= 4:  # Fri, Sat, Sun
            cycle = -0.02 * base_price if np.random.rand() > 0.3 else 0.0
            
        # 3. Promotional sales (sudden drops of 8-15%, lasting 1-3 days)
        is_promo = False
        days_since_last_promo = day - last_promo_day
        
        # Trigger promo if interval reached + some randomness, or if it's already active
        if days_since_last_promo >= promo_interval and np.random.rand() > 0.4:
            is_promo = True
            last_promo_day = day
            promo_duration = np.random.randint(1, 4)
            promo_discount = np.random.uniform(0.08, 0.16)
        elif 0 < day - last_promo_day < np.random.randint(2, 4):
            # Continue ongoing promo
            is_promo = True
            promo_discount = np.random.uniform(0.08, 0.16)
            
        discount = -promo_discount * base_price if is_promo else 0.0
        
        # 4. Daily noise (0.5% fluctuation)
        noise = np.random.normal(0, 0.005) * base_price
        
        # Compute day's price
        day_price = base_price + trend + cycle + discount + noise
        
        # Cap price so it doesn't go below 50% or above 110% of base
        day_price = max(base_price * 0.50, min(base_price * 1.10, day_price))
        prices.append(round(day_price, 2))
        
    df = pd.DataFrame({
        "date": dates,
        "price": prices
    })
    return df

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies time-series feature engineering on the price historical dataset.
    Extracts time cycles, rolling metrics, price lags, and days since last drop.
    """
    df = df.copy()
    
    # 1. Date features
    df["weekday"] = df["date"].dt.weekday
    df["day_of_month"] = df["date"].dt.day
    df["month"] = df["date"].dt.month
    
    # 2. Price lag features
    df["price_lag_1"] = df["price"].shift(1)
    df["price_lag_3"] = df["price"].shift(3)
    df["price_lag_7"] = df["price"].shift(7)
    
    # 3. Rolling metrics (moving averages)
    df["roll_mean_3"] = df["price"].rolling(window=3).mean()
    df["roll_mean_7"] = df["price"].rolling(window=7).mean()
    df["roll_std_7"] = df["price"].rolling(window=7).std()
    
    # 4. Time since last discount (price drop of >= 4%)
    df["pct_change_1"] = df["price"].pct_change(1)
    df["is_discount"] = (df["pct_change_1"] <= -0.04).astype(int)
    
    # Compute days since last discount
    days_since_discount = []
    current_counter = 10  # starting default
    for val in df["is_discount"]:
        if val == 1:
            current_counter = 0
        else:
            current_counter += 1
        days_since_discount.append(current_counter)
    df["days_since_discount"] = days_since_discount
    
    # Fill NaN values created by lags/rolling windows with baseline price
    df = df.ffill().bfill()
    return df

def train_forecasting_models(df: pd.DataFrame, base_price: float):
    """
    Trains models using historical engineered features:
    1. Regressor to forecast prices over the next 20 days.
    2. Classifier to predict probability of a >5% drop in the next 10 and 20 days.
    """
    df_feat = engineer_features(df)
    
    # Define feature columns
    features = [
        "weekday", "day_of_month", "month", 
        "price_lag_1", "price_lag_3", "price_lag_7", 
        "roll_mean_3", "roll_mean_7", "roll_std_7", 
        "days_since_discount"
    ]
    
    # Create target variable for Regressor: predicting price in N days
    # To keep model training simple and robust, we train one multi-step-ahead predictor 
    # or predict prices incrementally (autoregressive).
    # Here we will train a Regressor to predict the direct next price, and roll it forward.
    X = df_feat[features].iloc[:-1]
    y_reg = df_feat["price"].iloc[1:]
    
    regressor = RandomForestRegressor(n_estimators=50, random_state=42)
    regressor.fit(X, y_reg)
    
    # Create target variable for Classifiers:
    # Target 10: Is there a price drop >= 5% (relative to today's price) in the NEXT 10 days?
    # Target 20: Is there a price drop >= 5% in the NEXT 20 days?
    num_samples = len(df_feat)
    y_class_10 = []
    y_class_20 = []
    
    for i in range(num_samples):
        current_price = df_feat["price"].iloc[i]
        
        # Check window ahead
        price_ahead_10 = df_feat["price"].iloc[i+1 : i+11]
        price_ahead_20 = df_feat["price"].iloc[i+1 : i+21]
        
        has_drop_10 = int(any(p <= current_price * 0.95 for p in price_ahead_10)) if len(price_ahead_10) > 0 else 0
        has_drop_20 = int(any(p <= current_price * 0.95 for p in price_ahead_20)) if len(price_ahead_20) > 0 else 0
        
        y_class_10.append(has_drop_10)
        y_class_20.append(has_drop_20)
        
    df_feat["drop_target_10"] = y_class_10
    df_feat["drop_target_20"] = y_class_20
    
    # Train classification models
    X_cls = df_feat[features].iloc[:-20]  # trim end to avoid training on incomplete lookaheads
    y_cls_10 = df_feat["drop_target_10"].iloc[:-20]
    y_cls_20 = df_feat["drop_target_20"].iloc[:-20]
    
    classifier_10 = RandomForestClassifier(n_estimators=50, random_state=42)
    classifier_10.fit(X_cls, y_cls_10)
    
    classifier_20 = RandomForestClassifier(n_estimators=50, random_state=42)
    classifier_20.fit(X_cls, y_cls_20)
    
    return regressor, classifier_10, classifier_20, features

def get_predictions(product_name: str, base_price: float, forecast_days: int = 20) -> dict:
    """
    Generates historical data, runs feature engineering, trains models,
    and returns historical and forecasted prices, drop probabilities, and recommendations.
    """
    # 1. Generate history
    df_hist = generate_historical_prices(product_name, base_price)
    
    # 2. Train models
    reg, clf10, clf20, features_list = train_forecasting_models(df_hist, base_price)
    
    # 3. Perform forecasting for the next 20 days
    # We will simulate feature updating day-by-day to forecast prices autoregressively
    df_forecast = df_hist.copy()
    current_date = df_hist["date"].iloc[-1]
    
    forecast_prices = []
    forecast_dates = []
    
    # Keep track of rolling metrics dynamically for future steps
    for step in range(forecast_days):
        next_date = current_date + timedelta(days=step + 1)
        forecast_dates.append(next_date)
        
        # Calculate features based on the dataframe including previously predicted items
        df_feat_temp = engineer_features(df_forecast)
        latest_row = df_feat_temp.iloc[-1]
        
        # Format the feature vector for prediction
        x_pred = pd.DataFrame([latest_row[features_list]])
        pred_price = reg.predict(x_pred)[0]
        
        # Add slight decay/variation so it doesn't converge to a flat average
        weekday = next_date.weekday()
        if weekday >= 4 and np.random.rand() > 0.4:
            pred_price *= 0.985 # simulated weekend discount in forecast
            
        pred_price = round(max(base_price * 0.5, min(base_price * 1.1, pred_price)), 2)
        forecast_prices.append(pred_price)
        
        # Append predictions back to df_forecast to feed the next step's lags/rolling metrics
        new_row = pd.DataFrame([{"date": next_date, "price": pred_price}])
        df_forecast = pd.concat([df_forecast, new_row], ignore_index=True)
        
    # 4. Get deal probabilities for today (latest point in history)
    df_feat_latest = engineer_features(df_hist)
    latest_feat = pd.DataFrame([df_feat_latest.iloc[-1][features_list]])
    
    prob_drop_10 = round(float(clf10.predict_proba(latest_feat)[0][1] * 100), 1)
    prob_drop_20 = round(float(clf20.predict_proba(latest_feat)[0][1] * 100), 1)
    
    # 5. Formulate recommendations
    current_price = float(df_hist["price"].iloc[-1])
    min_predicted_price = min(forecast_prices)
    min_pred_index = forecast_prices.index(min_predicted_price)
    days_to_deal = min_pred_index + 1
    
    pot_savings_pct = round(((current_price - min_predicted_price) / current_price) * 100, 1)
    
    if prob_drop_10 >= 70.0 and pot_savings_pct >= 5.0:
        recommendation = "WAIT"
        reason = f"High probability ({prob_drop_10}%) of a price drop in the next 10 days. Estimated savings of up to {pot_savings_pct}%."
    elif prob_drop_20 >= 60.0 and pot_savings_pct >= 8.0:
        recommendation = "WAIT"
        reason = f"A solid deal is forecasted within the next 20 days (approx. day {days_to_deal})."
    else:
        recommendation = "BUY"
        reason = "Prices are expected to remain stable or rise. Current offer is optimal."
        
    # Format dates to string
    hist_list = [{"date": d.strftime("%Y-%m-%d"), "price": float(p)} for d, p in zip(df_hist["date"], df_hist["price"])]
    fore_list = [{"date": d.strftime("%Y-%m-%d"), "price": float(p)} for d, p in zip(forecast_dates, forecast_prices)]
    
    return {
        "product": product_name,
        "base_price": base_price,
        "current_price": current_price,
        "prob_drop_10": prob_drop_10,
        "prob_drop_20": prob_drop_20,
        "predicted_low": float(min_predicted_price),
        "days_to_low": days_to_deal,
        "potential_savings_pct": pot_savings_pct,
        "recommendation": recommendation,
        "reason": reason,
        "history": hist_list,
        "forecast": fore_list
    }

if __name__ == "__main__":
    print("Testing ML Predictor...")
    res = get_predictions("Sony WH-1000XM4", 349.99)
    print(f"Product: {res['product']}")
    print(f"Current Price: ${res['current_price']}")
    print(f"10-Day Deal Prob: {res['prob_drop_10']}%")
    print(f"20-Day Deal Prob: {res['prob_drop_20']}%")
    print(f"Recommendation: {res['recommendation']} - {res['reason']}")
    print(f"Forecast low: ${res['predicted_low']} on day {res['days_to_low']}")

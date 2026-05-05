from flask import Flask
import requests
import time
import ccxt
import pandas as pd
import threading

# ===== FLASK APP =====
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot is running 🚀"

# ===== SETTINGS =====
FIREBASE_URL = "https://signalapp-7ad01-default-rtdb.firebaseio.com/signals.json"
SYMBOL = "BTC/USDT"
TIMEFRAME = "15m"

# ===== EXCHANGE =====
exchange = ccxt.binance()

# ===== GET DATA =====
def get_data():
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=50)
    df = pd.DataFrame(ohlcv, columns=["time","open","high","low","close","volume"])

    # RSI
    delta = df["close"].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    # EMA
    df["ema"] = df["close"].ewm(span=20).mean()

    return df

# ===== SIGNAL LOGIC =====
def generate_signal():
    df = get_data()
    last = df.iloc[-1]

    rsi = last["rsi"]
    price = last["close"]
    ema = last["ema"]

    print(f"RSI: {rsi} | Price: {price} | EMA: {ema}")

    signal = None

    if rsi < 65:
        signal = {
            "pair": "BTCUSDT",
            "type": "BUY",
            "entry": str(round(price)),
            "tp": str(round(price + 1000)),
            "sl": str(round(price - 1000)),
            "timeframe": TIMEFRAME
        }

    elif rsi > 60:
        signal = {
            "pair": "BTCUSDT",
            "type": "SELL",
            "entry": str(round(price)),
            "tp": str(round(price - 1000)),
            "sl": str(round(price + 1000)),
            "timeframe": TIMEFRAME
        }

    return signal

# ===== SEND (REPLACE) =====
def send_to_firebase(signal):
    try:
        res = requests.put(FIREBASE_URL, json=signal)
        print("✅ Signal Replaced:", res.text)
    except Exception as e:
        print("❌ Error:", e)

# ===== BOT LOOP =====
def run_bot():
    while True:
        try:
            signal = generate_signal()
            if signal:
                print("🔥 NEW SIGNAL:", signal)
                send_to_firebase(signal)

        except Exception as e:
            print("❌ Bot Error:", e)

        time.sleep(60)

# ===== START BOTH (Flask + Bot) =====
if __name__ == "__main__":
    bot_thread = threading.Thread(target=run_bot)
    bot_thread.start()

    app.run(host="0.0.0.0", port=5000)
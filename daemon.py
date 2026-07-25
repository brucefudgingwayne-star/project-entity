import time
import requests
import json
import os
from datetime import datetime

WEBHOOK_FILE = "webhook_config.json"
DAEMON_LOG_FILE = "daemon_activity_log.json"
SYMBOL = "BTCUSDT"
CHECK_INTERVAL = 30  # seconds

def load_webhook():
    if os.path.exists(WEBHOOK_FILE):
        try:
            with open(WEBHOOK_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"url": "", "enabled": False}

def log_daemon_activity(entry):
    logs = []
    if os.path.exists(DAEMON_LOG_FILE):
        try:
            with open(DAEMON_LOG_FILE, "r") as f:
                logs = json.load(f)
        except:
            pass
    logs.insert(0, entry)
    # Keep last 50 logs
    if len(logs) > 50:
        logs = logs[:50]
    with open(DAEMON_LOG_FILE, "w") as f:
        json.dump(logs, f)

print("⚡ Project Entity Background Daemon Initialized...")
print(f"Monitoring {SYMBOL} order flow and RSI thresholds every {CHECK_INTERVAL}s...")

while True:
    config = load_webhook()
    timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval=1h&limit=20"
        res = requests.get(url, timeout=5).json()
        closes = [float(x[4]) for x in res]
        
        delta = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        gain = sum([d for d in delta[-14:] if d > 0]) / 14
        loss = sum([-d for d in delta[-14:] if d < 0]) / 14
        rs = gain / loss if loss > 0 else 100
        rsi = 100 - (100 / (1 + rs))
        current_price = closes[-1]
        
        print(f"[{timestamp_str}] {SYMBOL} Price: ${current_price:,.2f} | RSI: {rsi:.1f}")
        
        log_entry = {
            "Timestamp": timestamp_str,
            "Symbol": SYMBOL,
            "Price ($)": round(current_price, 2),
            "RSI (14H)": round(rsi, 1),
            "Status": "Normal Polling"
        }
        
        if config.get("enabled") and config.get("url"):
            if rsi >= 70 or rsi <= 30:
                payload = {
                    "content": f"🚨 **Project Entity Alert Daemon**\nTarget: {SYMBOL} | Price: ${current_price:,.2f}\nRSI Threshold Breached: **{rsi:.1f}**\nAction recommended: Review order book imbalance terminal."
                }
                requests.post(config["url"], json=payload, timeout=5)
                log_entry["Status"] = f"Alert Dispatched (RSI {rsi:.1f})"
                print(f"--> Alert successfully dispatched for RSI {rsi:.1f}!")
        
        log_daemon_activity(log_entry)
    except Exception as e:
        print(f"Daemon telemetry error: {str(e)}")
        
    time.sleep(CHECK_INTERVAL)
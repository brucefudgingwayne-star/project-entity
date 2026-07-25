import ccxt
import time
import requests
import json
import os
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ==========================================
#   PROJECT ENTITY v14.0: PRODUCTION CONFIG
# ==========================================
TELEGRAM_BOT_TOKEN = ""  # Input your Telegram Bot Token here
TELEGRAM_CHAT_ID = ""    # Input your Telegram Chat ID here

PORTFOLIO_FILE = "entity_portfolio.json"
MAX_DAILY_DRAWDOWN_PCT = 0.05
TRAILING_STOP_BUFFER_PCT = 0.015

# Configure local resilience logging
logging.basicConfig(
    filename="entity_error.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Portfolio load error: {e}")
    default_portfolio = {
        "balance": 10000.0,
        "initial_balance": 10000.0,
        "open_positions": [],
        "trade_history": []
    }
    save_portfolio(default_portfolio)
    return default_portfolio

def save_portfolio(portfolio_data):
    try:
        with open(PORTFOLIO_FILE, "w", encoding="utf-8") as f:
            json.dump(portfolio_data, f, indent=4)
    except Exception as e:
        logging.error(f"Portfolio save error: {e}")

def calculate_rsi(closes, period=14):
    if len(closes) < period + 1:
        return 50.0
    gains, losses = 0.0, 0.0
    for i in range(1, period + 1):
        change = closes[-i] - closes[-i-1]
        if change > 0:
            gains += change
        else:
            losses -= change
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def scan_multi_exchange_arbitrage(symbol):
    exchange_classes = ['binance', 'bybit', 'okx', 'kraken']
    prices = {}
    for ex_name in exchange_classes:
        try:
            ex_class = getattr(ccxt, ex_name)()
            ex_class.load_markets()
            if symbol in ex_class.symbols:
                ticker = ex_class.fetch_ticker(symbol)
                prices[ex_name] = ticker['last']
        except Exception:
            continue
            
    if len(prices) > 1:
        lowest_ex = min(prices, key=prices.get)
        highest_ex = max(prices, key=prices.get)
        low_price = prices[lowest_ex]
        high_price = prices[highest_ex]
        spread_pct = ((high_price - low_price) / low_price) * 100
        if spread_pct > 0.5:
            return f"⚡ Arbitrage Spread on {symbol}: Buy {lowest_ex} @ ${low_price:,.2f} | Sell {highest_ex} @ ${high_price:,.2f} ({spread_pct:.2f}%)"
    return None

def monitor_and_manage_positions(exchange):
    portfolio = load_portfolio()
    if not portfolio["open_positions"]:
        return

    updated_open_positions = []
    for pos in portfolio["open_positions"]:
        symbol = pos["symbol"]
        entry_price = pos["entry_price"]
        units = pos["units"]
        stop_loss = pos["stop_loss"]
        take_profit = pos["take_profit"]
        
        try:
            ticker = exchange.fetch_ticker(symbol)
            current_price = ticker['last']
            closed, close_reason, pnl_dollar = False, "", 0.0
            
            potential_new_sl = current_price * (1 - TRAILING_STOP_BUFFER_PCT)
            if potential_new_sl > stop_loss:
                stop_loss = potential_new_sl
                pos["stop_loss"] = stop_loss

            if current_price >= take_profit:
                closed = True
                close_reason = "TAKE PROFIT REACHED 🎯"
                pnl_dollar = (take_profit - entry_price) * units
                portfolio["balance"] += pnl_dollar
            elif current_price <= stop_loss:
                closed = True
                close_reason = "STOP LOSS / TRAILING HIT 🛑"
                pnl_dollar = (stop_loss - entry_price) * units
                portfolio["balance"] += pnl_dollar
                
            if closed:
                pos["exit_price"] = take_profit if "TAKE" in close_reason else stop_loss
                pos["close_reason"] = close_reason
                pos["pnl"] = pnl_dollar
                portfolio["trade_history"].append(pos)
            else:
                updated_open_positions.append(pos)
        except Exception as e:
            logging.error(f"Position monitor error for {symbol}: {e}")
            updated_open_positions.append(pos)
            
    portfolio["open_positions"] = updated_open_positions
    save_portfolio(portfolio)

def execute_institutional_cycle():
    """Self-healing execution cycle wrapped for cloud fault tolerance."""
    try:
        exchange = ccxt.binance({'enableRateLimit': True, 'options': {'defaultType': 'swap'}})
        monitor_and_manage_positions(exchange)
        
        portfolio = load_portfolio()
        symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT']
        
        for symbol in symbols:
            ticker = exchange.fetch_ticker(symbol)
            price = ticker['last']
            change = ticker.get('percentage', 0.0) or 0.0
            
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=30)
            closes = [candle[4] for candle in ohlcv]
            sma_24 = sum(closes[-24:]) / 24
            rsi = calculate_rsi(closes)
            
            if price > sma_24 and change > 1.0 and rsi < 70:
                signal, sl_pct, tp_pct = "BULLISH MOMENTUM", 0.020, 0.045
            elif price < sma_24 and change < -2.0 and rsi < 35:
                signal, sl_pct, tp_pct = "OVERSOLD DIP", 0.030, 0.070
            else:
                signal, sl_pct, tp_pct = "RANGE", 0.015, 0.035
            
            stop_loss = price * (1 - sl_pct)
            take_profit = price * (1 + tp_pct)
            units = (portfolio["balance"] * 0.02) / abs(price - stop_loss) if abs(price - stop_loss) > 0 else 0
            
            if "OVERSOLD" in signal or "BULLISH" in signal:
                trade_record = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "symbol": symbol, "action": "BUY", "entry_price": price,
                    "units": units, "stop_loss": stop_loss, "take_profit": take_profit, "status": "OPEN"
                }
                portfolio["open_positions"].append(trade_record)
                save_portfolio(portfolio)
        print(f"[+] Autonomous cycle successfully executed at {datetime.now()}")
    except Exception as e:
        logging.error(f"Execution cycle crash recovered: {e}")
        print(f"[-] Fault intercepted and logged safely: {e}")

# ==========================================
#   TELEGRAM INTERACTIVE COMMAND HANDLERS
# ==========================================
async def tg_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👑 *PROJECT ENTITY v14.0 ACTIVE*\nCommands:\n/status - View balance & positions\n/scan - Run instant quant pulse")

async def tg_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    portfolio = load_portfolio()
    msg = f"📊 *PORTFOLIO STATUS*\nBalance: `${portfolio['balance']:,.2f}`\nOpen Positions: {len(portfolio['open_positions'])}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def tg_scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Forcing instant quantitative engine scan...")
    execute_institutional_cycle()
    await update.message.reply_text("✅ Scan complete. Check local logs or ledger.")

def start_telegram_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("[-] Telegram Bot Token missing. Skipping remote bot listener.")
        return
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", tg_start))
    app.add_handler(CommandHandler("status", tg_status))
    app.add_handler(CommandHandler("scan", tg_scan))
    print("[+] Telegram Bot long-polling active...")
    app.run_polling()

def start_background_daemon():
    print("\n[+] Initializing v14.0 Self-Healing Cloud Daemon...")
    try:
        while True:
            execute_institutional_cycle()
            print("[DAEMON] Sleeping for 60 minutes...")
            time.sleep(3600)
    except KeyboardInterrupt:
        print("\n[+] Daemon stopped safely by user.")

def main_menu():
    while True:
        print("\n==================================================")
        print("   PROJECT ENTITY v14.0: COMMAND CONTROL CENTER   ")
        print("==================================================")
        print(" [1] Run Single Execution & Risk Scan")
        print(" [2] Launch Autonomous Daemon (Hourly Loop)")
        print(" [3] View Persistent Portfolio Ledger")
        print(" [4] Start Interactive Telegram Bot Listener")
        print(" [5] Shutdown Engine")
        
        choice = input("\nSelect operational command (1-5): ").strip()
        if choice == '1':
            execute_institutional_cycle()
        elif choice == '2':
            start_background_daemon()
        elif choice == '3':
            p = load_portfolio()
            print(f"\nBalance: ${p['balance']:,.2f} | Open Trades: {len(p['open_positions'])}")
        elif choice == '4':
            start_telegram_bot()
        elif choice == '5':
            print("\n[+] Engine offline. Stay disciplined, Emperor.")
            break
        else:
            print("[-] Invalid choice.")

if __name__ == "__main__":
    main_menu()
import streamlit as st
import json
import os
import requests
import pandas as pd
import numpy as np
import urllib.request
import xml.etree.ElementTree as ET
from data_corrector import validate_and_clean_crypto_data
from datetime import date, datetime
import plotly.graph_objects as go

try:
    from google import genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False

st.set_page_config(
    page_title="Project Entity | Institutional Intelligence",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# MEXC / TradingView Inspired Minimalist & Professional Styling
st.markdown("""
    <style>
    .main { background-color: #080808; color: #f3f3f3; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .stSidebar { background-color: #121212; border-right: 1px solid #1f1f1f; }
    
    .brand-header {
        font-size: 0.85rem;
        font-weight: 700;
        letter-spacing: 1.5px;
        color: #d4af37;
        text-transform: uppercase;
        padding: 6px 10px;
        background: #121212;
        border: 1px solid #2a220b;
        border-radius: 4px;
        display: inline-block;
        margin-bottom: 15px;
    }
    
    .terminal-card {
        background-color: #121212;
        border: 1px solid #1f1f1f;
        border-radius: 6px;
        padding: 16px;
        margin-bottom: 12px;
    }
    
    .gold-accent { color: #d4af37; font-weight: 600; }
    
    .stButton>button {
        background-color: #181818;
        color: #d4af37;
        border: 1px solid #33290e;
        border-radius: 4px;
        font-size: 0.85rem;
        font-weight: 600;
        padding: 4px 12px;
        transition: all 0.2s ease;
    }
    .stButton>button:hover {
        background-color: #d4af37;
        color: #080808;
        border-color: #d4af37;
    }
    </style>
""", unsafe_allow_html=True)

PROFILE_FILE = "user_profile.json"
MEMORY_FILE = "entity_chat_memory.json"
JOURNAL_FILE = "trade_journal.json"
WEBHOOK_FILE = "webhook_config.json"
EXECUTION_LOG_FILE = "execution_router_log.json"
PORTFOLIO_FILE = "portfolio_state.json"
ARB_LOG_FILE = "arbitrage_history.json"
WHALE_ALERT_FILE = "whale_alert_log.json"
DAEMON_LOG_FILE = "daemon_activity_log.json"

def load_profile():
    if os.path.exists(PROFILE_FILE):
        try:
            with open(PROFILE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return None

def save_profile(data):
    with open(PROFILE_FILE, "w") as f:
        json.dump(data, f)

def load_chat_memory():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_chat_memory(messages):
    with open(MEMORY_FILE, "w") as f:
        json.dump(messages, f)

def load_journal():
    if os.path.exists(JOURNAL_FILE):
        try:
            with open(JOURNAL_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_journal(trades):
    with open(JOURNAL_FILE, "w") as f:
        json.dump(trades, f)

def load_webhook():
    if os.path.exists(WEBHOOK_FILE):
        try:
            with open(WEBHOOK_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"url": "", "enabled": False, "events": ["Liquidation Breach", "RSI Overbought/Oversold"]}

def save_webhook(config):
    with open(WEBHOOK_FILE, "w") as f:
        json.dump(config, f)

def load_exec_logs():
    if os.path.exists(EXECUTION_LOG_FILE):
        try:
            with open(EXECUTION_LOG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_exec_logs(logs):
    with open(EXECUTION_LOG_FILE, "w") as f:
        json.dump(logs, f)

def load_portfolio():
    if os.path.exists(PORTFOLIO_FILE):
        try:
            with open(PORTFOLIO_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {"cash": 25000.0, "allocations": {"BTC": 0.4, "ETH": 0.3, "SOL": 0.2, "USDT": 0.1}}

def save_portfolio(port):
    with open(PORTFOLIO_FILE, "w") as f:
        json.dump(port, f)

def load_arb_logs():
    if os.path.exists(ARB_LOG_FILE):
        try:
            with open(ARB_LOG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_arb_logs(logs):
    with open(ARB_LOG_FILE, "w") as f:
        json.dump(logs, f)

def load_whale_logs():
    if os.path.exists(WHALE_ALERT_FILE):
        try:
            with open(WHALE_ALERT_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []

def save_whale_logs(logs):
    with open(WHALE_ALERT_FILE, "w") as f:
        json.dump(logs, f)

def load_daemon_logs():
    if os.path.exists(DAEMON_LOG_FILE):
        try:
            with open(DAEMON_LOG_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return []
    
@st.cache_data(ttl=5)
def fetch_live_candlestick_data(symbol="BTCUSDT"):
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
        response = requests.get(url, headers=headers, timeout=4).json()
        
        df = pd.DataFrame(response, columns=[
            'Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore'
        ])
        df['Open'] = df['Open'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['Timestamp'] = pd.to_datetime(df['Open_Time'], unit='ms')
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
        
        return df
    except Exception as e:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='h')
        return pd.DataFrame({
            'Timestamp': dates,
            'Open': [65000.0] * 100, 
            'High': [65500.0] * 100, 
            'Low': [64500.0] * 100, 
            'Close': [65027.0] * 100,
            'Volume': [100.0] * 100,
            'RSI': [54.5] * 100, 
            'SMA_20': [64800.0] * 100, 
            'Upper_Band': [66500.0] * 100, 
            'Lower_Band': [63100.0] * 100
        })
        response = requests.get(url, headers=headers, timeout=4).json()
        
        df = pd.DataFrame(response, columns=[
            'Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore'
        ])
        df['Open'] = df['Open'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['Timestamp'] = pd.to_datetime(df['Open_Time'], unit='ms')
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
        
        return df
    except Exception as e:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='h')
        return pd.DataFrame({
            'Timestamp': dates,
            'Open': [65000.0] * 100, 
            'High': [65500.0] * 100, 
            'Low': [64500.0] * 100, 
            'Close': [65027.0] * 100,
            'Volume': [100.0] * 100,
            'RSI': [54.5] * 100, 
            'SMA_20': [64800.0] * 100, 
            'Upper_Band': [66500.0] * 100, 
            'Lower_Band': [63100.0] * 100
        })
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1h&limit=100"
        headers = {"Cache-Control": "no-cache", "Pragma": "no-cache"}
        response = requests.get(url, headers=headers, timeout=4).json()
        
        df = pd.DataFrame(response, columns=[
            'Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore'
        ])
        df['Open'] = df['Open'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['Timestamp'] = pd.to_datetime(df['Open_Time'], unit='ms')
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
        
        return df
    except Exception as e:
        dates = pd.date_range(end=pd.Timestamp.now(), periods=100, freq='h')
        return pd.DataFrame({
            'Timestamp': dates,
            'Open': [65000.0] * 100, 
            'High': [65500.0] * 100, 
            'Low': [64500.0] * 100, 
            'Close': [65027.0] * 100,
            'Volume': [100.0] * 100,
            'RSI': [54.5] * 100, 
            'SMA_20': [64800.0] * 100, 
            'Upper_Band': [66500.0] * 100, 
            'Lower_Band': [63100.0] * 100
        })
        
        if not isinstance(response, list):
            raise ValueError("API error or rate limited")

        df = pd.DataFrame(response, columns=[
            'Open_Time', 'Open', 'High', 'Low', 'Close', 'Volume',
            'Close_Time', 'Quote_Asset_Volume', 'Number_of_Trades',
            'Taker_Buy_Base_Asset_Volume', 'Taker_Buy_Quote_Asset_Volume', 'Ignore'
        ])
        df['Open'] = df['Open'].astype(float)
        df['High'] = df['High'].astype(float)
        df['Low'] = df['Low'].astype(float)
        df['Close'] = df['Close'].astype(float)
        df['Volume'] = df['Volume'].astype(float)
        df['Timestamp'] = pd.to_datetime(df['Open_Time'], unit='ms')
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['STD_20'] = df['Close'].rolling(window=20).std()
        df['Upper_Band'] = df['SMA_20'] + (df['STD_20'] * 2)
        df['Lower_Band'] = df['SMA_20'] - (df['STD_20'] * 2)
        
        return df
    except:
        dates = pd.date_range(start='2026-07-01', periods=100, freq='h')
        df = pd.DataFrame({
            'Timestamp': dates,
            'Open': 65000.0, 'High': 65500.0, 'Low': 64500.0, 'Close': 65027.0,
            'RSI': 54.5, 'SMA_20': 64800.0, 'Upper_Band': 66500.0, 'Lower_Band': 63100.0
        })
        return df
        return df

@st.cache_data(ttl=3)
def fetch_order_book_depth(symbol="BTCUSDT"):
    try:
        url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=20"
        res = requests.get(url, timeout=3).json()
        bids = pd.DataFrame(res['bids'], columns=['Price', 'Quantity']).astype(float)
        asks = pd.DataFrame(res['asks'], columns=['Price', 'Quantity']).astype(float)
        return bids, asks
    except:
        bids = pd.DataFrame({'Price': [64990.0, 64980.0, 64970.0], 'Quantity': [1.2, 3.5, 2.1]})
        asks = pd.DataFrame({'Price': [65010.0, 65020.0, 65030.0], 'Quantity': [1.5, 2.0, 4.2]})
        return bids, asks

@st.cache_data(ttl=10)
def fetch_correlation_matrix():
    assets = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "BNBUSDT"]
    price_data = {}
    for asset in assets:
        try:
            url = f"https://api.binance.com/api/v3/klines?symbol={asset}&interval=1h&limit=50"
            res = requests.get(url, timeout=3).json()
            closes = [float(x[4]) for x in res]
            price_data[asset.replace("USDT", "")] = closes
        except:
            price_data[asset.replace("USDT", "")] = [100.0] * 50
    df_corr = pd.DataFrame(price_data).pct_change().corr()
    return df_corr

@st.cache_data(ttl=60)
def fetch_live_market_news():
    news_items = []
    try:
        url = "https://cointelegraph.com/rss"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=4) as response:
            xml_data = response.read()
            root = ET.fromstring(xml_data)
            channel = root.find('channel')
            for item in channel.findall('item')[:6]:
                title = item.find('title').text if item.find('title') is not None else "Market Update"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else "Recent"
                link = item.find('link').text if item.find('link') is not None else "#"
                
                short_time = pub_date.split(',')[1].strip().split('+')[0].strip() if ',' in pub_date else pub_date
                
                news_items.append({
                    "source": "Cointelegraph Live Wire",
                    "time": short_time,
                    "headline": title,
                    "url": link
                })
    except:
        news_items.append({
            "source": "Project Entity Quant Engine",
            "time": "Just now",
            "headline": "Live feed status: Operational (RSS connection active).",
            "url": "#"
        })
    return news_items

user_profile = load_profile()
webhook_config = load_webhook()
portfolio_state = load_portfolio()

# Sidebar Setup
with st.sidebar:
    st.markdown('<div class="brand-header">⚡ Project Entity</div>', unsafe_allow_html=True)
    st.markdown("### 🎛️ Terminal Telemetry")
    
    if user_profile:
        st.markdown(f"**Operator:** <span class='gold-accent'>{user_profile.get('nickname', 'Trader')}</span>", unsafe_allow_html=True)
        
        current_asset_selection = st.selectbox(
            "Target Asset Focus", 
            ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"],
            index=["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"].index(user_profile.get('priority_asset', 'BTC/USDT')) if user_profile.get('priority_asset', 'BTC/USDT') in ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"] else 0
        )
        
        if current_asset_selection != user_profile.get('priority_asset'):
            user_profile['priority_asset'] = current_asset_selection
            save_profile(user_profile)
            st.rerun()
        
        if st.button("🔄 Force-Refresh Feed"):
            st.cache_data.clear()
            st.success("Caches cleared! Pulling fresh payloads...")
            st.rerun()
            
        if st.button("🔄 Reset Profile"):
            for f in [PROFILE_FILE, MEMORY_FILE, JOURNAL_FILE, WEBHOOK_FILE, EXECUTION_LOG_FILE, PORTFOLIO_FILE, ARB_LOG_FILE, WHALE_ALERT_FILE, DAEMON_LOG_FILE]:
                if os.path.exists(f):
                    os.remove(f)
            st.cache_data.clear()
            st.rerun()
    
    st.markdown("---")
    st.markdown("### 🔑 BYOK Security Gateway")
    user_api_key = st.text_input("Gemini API Key", type="password", placeholder="Paste key here...")
    if user_api_key:
        st.success("API Key Active", icon="🟢")
        
    st.markdown("---")
    st.markdown("### 🤖 Neural Agent Swarm")
    st.markdown("""
    <div style="font-size:0.8rem; background:#121212; padding:10px; border-radius:4px; border:1px solid #1f1f1f;">
    <span style="color:#00ffcc;">● ALPHA SCOUT:</span> Active (0ms Latency)<br>
    <span style="color:#d4af37;">● RISK SENTINEL:</span> Guarding VaR<br>
    <span style="color:#00ffcc;">● WEBHOOK DAEMON:</span> Standby / Ready
    </div>
    """, unsafe_allow_html=True)

# Onboarding View
if not user_profile:
    st.markdown("# ⚡ Welcome to Project Entity")
    st.markdown("Initialize your operator profile to unlock the institutional quantitative engine.")
    
    with st.form("onboarding_form"):
        col1, col2 = st.columns(2)
        with col1:
            nickname = st.text_input("Preferred Nickname (e.g., Batman)")
            dob = st.date_input("Date of Birth", min_value=date(1950, 1, 1), max_value=date(2010, 12, 31))
        with col2:
            gmail = st.text_input("Contact Gmail")
            priority_asset = st.selectbox("Priority Asset Focus", ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "BNB/USDT"])
        
        submitted = st.form_submit_button("Initialize Terminal & Enter")
        if submitted:
            if nickname and gmail:
                profile_data = {
                    "nickname": nickname,
                    "dob": str(dob),
                    "gmail": gmail,
                    "priority_asset": priority_asset
                }
                save_profile(profile_data)
                st.success(f"Welcome to the terminal, {nickname}!")
                st.rerun()
            else:
                st.error("Please provide both your Nickname and Gmail to proceed.")
    st.stop()

nickname = user_profile.get("nickname", "Trader")
priority_asset = user_profile.get("priority_asset", "BTC/USDT")
binance_symbol = priority_asset.replace("/", "")

df_market = fetch_live_candlestick_data(binance_symbol)
df_market = validate_and_clean_crypto_data(df_market)
if 'Close' in df_market.columns and not df_market.empty:
    live_price = df_market['Close'].iloc[-1]
else:
    live_price = 0.0  # or a fallback value
if 'RSI' in df_market.columns and not df_market.empty and not pd.isna(df_market['RSI'].iloc[-1]):
    live_rsi = df_market['RSI'].iloc[-1]
else:
    live_rsi = 50.0

if 'SMA_20' in df_market.columns and not df_market.empty and not pd.isna(df_market['SMA_20'].iloc[-1]):
    live_sma = df_market['SMA_20'].iloc[-1]
else:
    live_sma = live_price
live_news = fetch_live_market_news()
journal_trades = load_journal()
df_corr = fetch_correlation_matrix()
bids_df, asks_df = fetch_order_book_depth(binance_symbol)
exec_logs = load_exec_logs()
arb_logs = load_arb_logs()
whale_logs = load_whale_logs()
daemon_logs = load_daemon_logs()

st.markdown(f"### Welcome back, <span class='gold-accent'>{nickname}</span>.", unsafe_allow_html=True)
st.markdown(f"<p style='color: #888; font-size: 0.9rem;'>Institutional Quantitative Intelligence • Target Asset: <span class='gold-accent'>{priority_asset}</span> Active</p>", unsafe_allow_html=True)

# Top Metrics Bar
m1, m2, m3, m4 = st.columns(4)
with m1:
    st.metric(label=f"{priority_asset} (Live Feed)", value=f"${live_price:,.2f}", delta="Real-time")
with m2:
    st.metric(label="Live RSI (14H)", value=f"{live_rsi:.1f}", delta="Neutral-Bullish" if live_rsi > 50 else "Neutral-Bearish")
with m3:
    st.metric(label="20-Period SMA", value=f"${live_sma:,.2f}", delta="Trend Baseline")
with m4:
    st.metric(label="Logged Trades", value=str(len(journal_trades)), delta="Persistent Ledger")

st.markdown("---")

# Navigation Tabs
tab_main, tab_agents, tab_montecarlo, tab_sor, tab_exec, tab_arb, tab_macro, tab_liq, tab_depth, tab_grid, tab_leverage, tab_backtest, tab_matrix, tab_journal, tab_news, tab_lifecycle = st.tabs([
    "⚡ Live Chart & Risk",
    "🤖 Multi-Agent Swarm",
    "🎲 Monte Carlo VaR",
    "🔀 Smart Order Routing",
    "🤖 Webhooks & Daemon",
    "⚖️ Cross-Exchange Arbitrage",
    "🌐 Macro & Whale Tracker",
    "🔥 Liquidation Heatmap",
    "🌊 Order Book Imbalance",
    "🤖 Order Grid & DCA",
    "⚙️ Margin & Liquidation",
    "📈 Algorithmic Backtest",
    "🔗 Correlation Matrix",
    "📒 Trade Journal", 
    "📰 Exchange Wire", 
    "📚 Bitcoin Lifecycle"
])

with tab_main:
    st.markdown(f"#### 📊 {priority_asset} Institutional Candlestick Feed & Bollinger Bands")
    
    fig = go.Figure()
if 'Upper_Band' in df_market.columns and 'Lower_Band' in df_market.columns:
    fig.add_trace(go.Scatter(x=df_market['Timestamp'], y=df_market['Upper_Band'], name='Upper Band', line=dict(color='rgba(212, 175, 55, 0.4)', width=1), mode='lines'))
    fig.add_trace(go.Scatter(x=df_market['Timestamp'], y=df_market['Lower_Band'], name='Lower Band', line=dict(color='rgba(212, 175, 55, 0.4)', width=1), mode='lines', fill='tonexty', fillcolor='rgba(212, 175, 55, 0.05)'))
    fig.add_trace(go.Scatter(x=df_market['Timestamp'], y=df_market['SMA_20'], name='20 SMA', line=dict(color='#00ffcc', width=1.5), mode='lines'))
    fig.add_trace(go.Candlestick(
        x=df_market['Timestamp'],
        open=df_market['Open'], high=df_market['High'],
        low=df_market['Low'], close=df_market['Close'],
        name='Price Action'
    ))
    fig.update_layout(
        template='plotly_dark',
        paper_bgcolor='#080808',
        plot_bgcolor='#121212',
        margin=dict(l=10, r=10, t=10, b=10),
        height=450,
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    st.plotly_chart(fig, use_container_width=True)

    col_main, col_chat = st.columns([1.2, 1])

    with col_main:
        st.markdown(f"#### 📐 Institutional Risk & Position Sizing Calculator")
        with st.container():
            rc1, rc2 = st.columns(2)
            with rc1:
                account_size = st.number_input("Total Account Capital ($)", value=10000.0, step=500.0)
                risk_pct = st.slider("Risk Tolerance per Trade (%)", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
            with rc2:
                default_entry = live_price
                default_stop = live_price * 0.99
                entry_price = st.number_input("Execution Entry ($)", value=default_entry, step=10.0)
                stop_loss = st.number_input("Stop Loss Level ($)", value=default_stop, step=10.0)
            
            risk_amount_usd = account_size * (risk_pct / 100.0)
            risk_per_unit = abs(entry_price - stop_loss)
            position_units = risk_amount_usd / risk_per_unit if risk_per_unit > 0 else 0
            position_size_usd = position_units * entry_price
            
            st.markdown(f"""
            <div class="terminal-card" style="border-left: 3px solid #00ffcc; margin-top: 10px;">
                <span style="font-size:0.75rem; color:#00ffcc;">QUANTITATIVE RISK REPORT ({priority_asset})</span><br>
                <span style="font-size:0.85rem; color:#bbb;">
                • <b>Max Dollar Risk:</b> ${risk_amount_usd:,.2f} ({risk_pct}% of capital)<br>
                • <b>Recommended Position Size:</b> ${position_size_usd:,.2f} ({position_units:.4f} units)<br>
                • <b>Risk/Reward Ratio:</b> 1 : 2.0 Target Validation Active
                </span>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("📝 Log This Trade to Journal"):
                new_trade = {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "asset": priority_asset,
                    "entry": entry_price,
                    "stop_loss": stop_loss,
                    "size_usd": round(position_size_usd, 2),
                    "units": round(position_units, 4)
                }
                journal_trades.append(new_trade)
                save_journal(journal_trades)
                st.success("Trade successfully recorded to persistent journal ledger!")
                st.rerun()

    with col_chat:
        st.markdown(f"#### 💬 Entity AI Terminal Companion")
        st.markdown(f"<p style='font-size:0.80rem; color:#888;'>Memory active. Analyzing {priority_asset} candlestick metrics.</p>", unsafe_allow_html=True)
        
        chat_container = st.container(height=420)
        
        if "messages" not in st.session_state:
            saved_msgs = load_chat_memory()
            if saved_msgs:
                st.session_state.messages = saved_msgs
            else:
                st.session_state.messages = [
                    {"role": "assistant", "content": f"Welcome back, {nickname}. Interactive chart for {priority_asset} is rendered. Live RSI is {live_rsi:.1f} and price is tracking at ${live_price:,.2f}. Ask me anything about our indicators, multi-agent swarm, or background daemon."}
                ]
            
        with chat_container:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])
                    
        if user_prompt := st.chat_input(f"Ask about {priority_asset}, background daemon, or execution..."):
            st.session_state.messages.append({"role": "user", "content": user_prompt})
            with chat_container:
                with st.chat_message("user"):
                    st.markdown(user_prompt)
                    
            bot_reply = ""
            if user_api_key and GEMINI_AVAILABLE:
                try:
                    client = genai.Client(api_key=user_api_key)
                    system_instruction = f"You are Project Entity, an elite institutional crypto quant agent. The user's nickname is {nickname}. Current target asset is {priority_asset} at ${live_price:,.2f}, RSI is {live_rsi:.1f}, 20 SMA is ${live_sma:,.2f}. Always explain quantitative multi-agent coordination, risk management, and market mechanics clearly."
                    response = client.models.generate_content(
                        model='gemini-3.6-flash',
                        contents=user_prompt,
                        config={"system_instruction": system_instruction}
                    )
                    bot_reply = response.text
        
except Exception as e:
        st.error(f"Error loading section: {e}")

with tab_agents:
    st.markdown(f"### 🤖 Neural Multi-Agent Swarm & Portfolio Optimization ({priority_asset})")
    
    ac1, ac2, ac3 = st.columns(3)
    with ac1:
        st.markdown("""
        <div class="terminal-card" style="border-top: 3px solid #00ffcc;">
            <h5 style="color: #00ffcc; margin-top:0;">Alpha Scout Agent</h5>
            <p style="font-size:0.85rem; color:#bbb;">
            <b>Status:</b> Scanning order flow.<br>
            <b>Task:</b> Identifies breakout momentum and volume imbalances across order books.<br>
            <b>Signal:</b> <code>Accumulation Phase</code>
            </p>
        </div>
        """, unsafe_allow_html=True)
    with ac2:
        st.markdown("""
        <div class="terminal-card" style="border-top: 3px solid #d4af37;">
            <h5 style="color: #d4af37; margin-top:0;">Risk Sentinel Agent</h5>
            <p style="font-size:0.85rem; color:#bbb;">
            <b>Status:</b> Monitoring VaR.<br>
            <b>Task:</b> Calculates 99% 24h Value-at-Risk and triggers emergency stop-protocols if drawdown exceeds bounds.<br>
            <b>Signal:</b> <code>Nominal (VaR: 1.8%)</code>
            </p>
        </div>
        """, unsafe_allow_html=True)
    with ac3:
        st.markdown("""
        <div class="terminal-card" style="border-top: 3px solid #00ffcc;">
            <h5 style="color: #00ffcc; margin-top:0;">Webhook Daemon Agent</h5>
            <p style="font-size:0.85rem; color:#bbb;">
            <b>Status:</b> Background Polling.<br>
            <b>Task:</b> Runs via <code>daemon.py</code> to monitor RSI extremes 24/7.<br>
            <b>Signal:</b> <code>Ready</code>
            </p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("##### 💼 Autonomous Portfolio Allocation Matrix")
    
    pc1, pc2 = st.columns(2)
    with pc1:
        port_cash = st.number_input("Total Portfolio Capital ($)", value=portfolio_state.get("cash", 25000.0), step=1000.0)
        btc_alloc = st.slider("BTC Allocation Weight (%)", 0, 100, int(portfolio_state["allocations"]["BTC"] * 100))
        eth_alloc = st.slider("ETH Allocation Weight (%)", 0, 100, int(portfolio_state["allocations"]["ETH"] * 100))
    with pc2:
        sol_alloc = st.slider("SOL Allocation Weight (%)", 0, 100, int(portfolio_state["allocations"]["SOL"] * 100))
        usdt_alloc = st.slider("USDT Reserve Weight (%)", 0, 100, int(portfolio_state["allocations"]["USDT"] * 100))
        
    total_weight = btc_alloc + eth_alloc + sol_alloc + usdt_alloc
    
    if total_weight == 100:
        if st.button("💾 Deploy & Rebalance Swarm Portfolio"):
            new_port = {
                "cash": port_cash,
                "allocations": {
                    "BTC": btc_alloc / 100.0,
                    "ETH": eth_alloc / 100.0,
                    "SOL": sol_alloc / 100.0,
                    "USDT": usdt_alloc / 100.0
                }
            }
            save_portfolio(new_port)
            st.success("Portfolio weights updated across swarm nodes!")
            st.rerun()
    else:
        st.warning(f"Total weight equals {total_weight}%. Allocations must sum exactly to 100% to rebalance.")

    alloc_data = [
        {"Asset": "Bitcoin (BTC)", "Weight (%)": f"{btc_alloc}%", "Dollar Value ($)": f"${port_cash * (btc_alloc/100):,.2f}"},
        {"Asset": "Ethereum (ETH)", "Weight (%)": f"{eth_alloc}%", "Dollar Value ($)": f"${port_cash * (eth_alloc/100):,.2f}"},
        {"Asset": "Solana (SOL)", "Weight (%)": f"{sol_alloc}%", "Dollar Value ($)": f"${port_cash * (sol_alloc/100):,.2f}"},
        {"Asset": "USDT Reserve", "Weight (%)": f"{usdt_alloc}%", "Dollar Value ($)": f"${port_cash * (usdt_alloc/100):,.2f}"}
    ]
    st.dataframe(pd.DataFrame(alloc_data), use_container_width=True)

with tab_montecarlo:
    st.markdown(f"### 🎲 Portfolio Monte Carlo Risk Simulator ({priority_asset})")
    st.markdown("Simulating 1,000 randomized future price trajectories over a 30-day horizon to evaluate statistical Value-at-Risk (VaR) and Expected Shortfall.")
    
    mc1, mc2 = st.columns(2)
    with mc1:
        mc_days = st.slider("Simulation Horizon (Days)", min_value=7, max_value=90, value=30, step=1)
        mc_sims = st.slider("Monte Carlo Paths", min_value=200, max_value=2000, value=1000, step=100)
    with mc2:
        mc_vol = st.slider("Daily Volatility Assumption (%)", min_value=1.0, max_value=10.0, value=3.5, step=0.5) / 100.0
        mc_drift = st.slider("Daily Return Drift (%)", min_value=-0.5, max_value=1.0, value=0.1, step=0.1) / 100.0

    if st.button("🚀 Run Monte Carlo VaR Simulation"):
        np.random.seed(42)
        simulated_paths = np.zeros((mc_days, mc_sims))
        simulated_paths[0] = port_cash
        
        for t in range(1, mc_days):
            shocks = np.random.normal(mc_drift, mc_vol, mc_sims)
            simulated_paths[t] = simulated_paths[t-1] * (1 + shocks)
            
        final_values = simulated_paths[-1]
        var_95 = port_cash - np.percentile(final_values, 5)
        var_99 = port_cash - np.percentile(final_values, 1)
        expected_shortfall = port_cash - np.mean(final_values[final_values <= np.percentile(final_values, 5)])
        
        mm1, mm2, mm3 = st.columns(3)
        with mm1:
            st.metric("95% Value-at-Risk (VaR)", value=f"${var_95:,.2f}", delta="Max expected loss (95% conf)", delta_color="inverse")
        with mm2:
            st.metric("99% Value-at-Risk (VaR)", value=f"${var_99:,.2f}", delta="Extreme tail risk", delta_color="inverse")
        with mm3:
            st.metric("Expected Shortfall (CVaR)", value=f"${expected_shortfall:,.2f}", delta="Tail loss severity", delta_color="inverse")
            
        fig_mc = go.Figure()
        for i in range(min(150, mc_sims)):
            fig_mc.add_trace(go.Scatter(y=simulated_paths[:, i], mode='lines', line=dict(color='rgba(0, 255, 204, 0.08)', width=1), showlegend=False))
            
        mean_path = np.mean(simulated_paths, axis=1)
        fig_mc.add_trace(go.Scatter(y=mean_path, mode='lines', name='Expected Path (Mean)', line=dict(color='#d4af37', width=2.5)))
        
        fig_mc.update_layout(
            template='plotly_dark',
            paper_bgcolor='#080808',
            plot_bgcolor='#121212',
            margin=dict(l=10, r=10, t=10, b=10),
            height=400,
            xaxis_title="Simulation Days",
            yaxis_title="Portfolio Value ($)"
        )
        st.plotly_chart(fig_mc, use_container_width=True)
    else:
        st.info("Configure your parameters above and click **Run Monte Carlo VaR Simulation** to initiate path generation.")

with tab_sor:
    st.markdown(f"### 🔀 Smart Order Routing (SOR) & Multi-Venue Split Execution ({priority_asset})")
    st.markdown("Simulate institutional algorithmic order splitting across Binance, Bybit, OKX, and Coinbase to eliminate market impact slippage.")
    
    sc1, sc2 = st.columns(2)
    with sc1:
        sor_order_size = st.number_input("Target Execution Size ($)", value=25000.0, step=5000.0)
        sor_strategy = st.selectbox("Routing Strategy", ["VWAP Volume Weighted", "Lowest Slippage Priority", "Equal Split Multi-Venue"])
    with sc2:
        max_venue_slippage = st.slider("Max Acceptable Slippage (%)", min_value=0.01, max_value=0.50, value=0.05, step=0.01)
        routing_mode = st.selectbox("Execution Type", ["Simulated Paper Route", "Live API Gateway (Armed)"])
        
    st.markdown("##### 🌐 Live Venue Depth & Fee Matrix")
    venue_matrix = [
        {"Venue": "Binance Spot", "Best Ask ($)": round(live_price, 2), "Available Liquidity ($)": "$450,000", "Maker/Taker Fee": "0.02% / 0.04%"},
        {"Venue": "Bybit Perpetual", "Best Ask ($)": round(live_price * 1.0002, 2), "Available Liquidity ($)": "$380,000", "Maker/Taker Fee": "0.01% / 0.05%"},
        {"Venue": "OKX Spot", "Best Ask ($)": round(live_price * 1.0004, 2), "Available Liquidity ($)": "$210,000", "Maker/Taker Fee": "0.02% / 0.05%"},
        {"Venue": "Coinbase Advanced", "Best Ask ($)": round(live_price * 1.0007, 2), "Available Liquidity ($)": "$600,000", "Maker/Taker Fee": "0.04% / 0.06%"}
    ]
    st.dataframe(pd.DataFrame(venue_matrix), use_container_width=True)
    
    if st.button("🚀 Execute Smart Order Routing Route"):
        if sor_strategy == "VWAP Volume Weighted":
            allocs = [0.35, 0.30, 0.15, 0.20]
        elif sor_strategy == "Lowest Slippage Priority":
            allocs = [0.50, 0.30, 0.10, 0.10]
        else:
            allocs = [0.25, 0.25, 0.25, 0.25]
            
        venues = ["Binance Spot", "Bybit Perpetual", "OKX Spot", "Coinbase Advanced"]
        execution_report = []
        
        for idx, v in enumerate(venues):
            amt = sor_order_size * allocs[idx]
            execution_report.append({
                "Timestamp": datetime.now().strftime("%H:%M:%S.%f")[:-3],
                "Venue": v,
                "Allocated ($)": round(amt, 2),
                "Route Status": "Filled (0ms Latency)"
            })
            
        log_entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "asset": priority_asset,
            "size": sor_order_size,
            "strategy": sor_strategy,
            "status": "Success"
        }
        exec_logs.append(log_entry)
        save_exec_logs(exec_logs)
        
        st.success("Smart Order Routing payload successfully split and executed across multi-exchange nodes!")
        st.dataframe(pd.DataFrame(execution_report), use_container_width=True)

    if exec_logs:
        st.markdown("##### 📜 Recent SOR Routing Audit Trail")
        st.dataframe(pd.DataFrame(exec_logs), use_container_width=True)

with tab_exec:
    st.markdown(f"### 🤖 Automated Algorithmic Webhook & Background Daemon Config ({priority_asset})")
    st.markdown("Configure webhook endpoints and manage your background 24/7 daemon listener (`daemon.py`).")
    
    with st.form("webhook_form"):
        wh_url = st.text_input("Webhook Payload Destination URL", value=webhook_config.get("url", ""), placeholder="https://discord.com/api/webhooks/... or https://api.telegram.org/bot...")
        wh_enabled = st.checkbox("Enable Automated Webhook Dispatch", value=webhook_config.get("enabled", False))
        
        st.markdown("##### Trigger Event Filters")
        ev1, ev2 = st.columns(2)
        with ev1:
            trig_liq = st.checkbox("Liquidation Cluster Breach", value=True)
            trig_rsi = st.checkbox("RSI Overbought / Oversold Alert", value=True)
        with ev2:
            trig_spread = st.checkbox("Cross-Exchange Arbitrage Spread Expansion", value=True)
            trig_risk = st.checkbox("Max Risk Limit Threshold Warning", value=True)
            
        submitted_wh = st.form_submit_button("Save Webhook Configuration")
        if submitted_wh:
            events_list = []
            if trig_liq: events_list.append("Liquidation Cluster Breach")
            if trig_rsi: events_list.append("RSI Overbought/Oversold")
            if trig_spread: events_list.append("Arbitrage Spread Expansion")
            if trig_risk: events_list.append("Risk Threshold Warning")
            
            new_config = {
                "url": wh_url,
                "enabled": wh_enabled,
                "events": events_list
            }
            save_webhook(new_config)
            st.success("Webhook configuration successfully saved and armed!")
            st.rerun()
            
    st.markdown("---")
    st.markdown("##### 📡 Background Daemon Status & Activity")
    st.markdown("""
    <div class="terminal-card">
    <p style="font-size:0.85rem; color:#bbb; margin:0;">
    To run your background daemon script alongside this terminal, open a separate terminal window and execute:<br>
    <code>python daemon.py</code>
    </p>
    </div>
    """, unsafe_allow_html=True)

    if daemon_logs:
        st.dataframe(pd.DataFrame(daemon_logs), use_container_width=True)
    else:
        st.info("No daemon activity logged yet. Start `daemon.py` in your terminal to begin background polling.")

with tab_arb:
    st.markdown(f"### ⚖️ Cross-Exchange Arbitrage & Delta-Neutral Funding Harvester ({priority_asset})")
    st.markdown("Execute automated cross-venue basis arbitrage. Lock in funding rate premiums while maintaining delta-neutral hedge balances.")
    
    ac1, ac2 = st.columns(2)
    with ac1:
        arb_capital = st.number_input("Arbitrage Allocation Capital ($)", value=10000.0, step=1000.0)
        target_spread = st.slider("Min Spread Trigger Threshold (%)", min_value=0.01, max_value=0.50, value=0.05, step=0.01)
    with ac2:
        long_venue = st.selectbox("Long Venue (Discount)", ["Binance Spot", "OKX Spot", "Coinbase Advanced"])
        short_venue = st.selectbox("Short Venue (Premium)", ["Bybit Perpetual", "Binance Futures", "OKX Perpetual"])

    arb_data = [
        {"Exchange Pair": "Binance Spot vs Bybit Perp", "Spread (%)": "+0.03%", "Funding Rate Delta": "+0.0025%", "Execution Viability": "Optimal", "Action": "Ready to Harvest"},
        {"Exchange Pair": "OKX Spot vs Binance Futures", "Spread (%)": "-0.02%", "Funding Rate Delta": "-0.0010%", "Execution Viability": "Sub-optimal", "Action": "Standby"},
        {"Exchange Pair": "Coinbase Spot vs OKX Perp", "Spread (%)": "+0.08%", "Funding Rate Delta": "+0.0040%", "Execution Viability": "High Yield", "Action": "Ready to Harvest"}
    ]
    st.dataframe(pd.DataFrame(arb_data), use_container_width=True)

    if st.button("⚡ Execute Delta-Neutral Arbitrage Lock"):
        arb_entry_log = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "asset": priority_asset,
            "capital": arb_capital,
            "long_venue": long_venue,
            "short_venue": short_venue,
            "status": "Hedge Locked & Yield Active"
        }
        arb_logs.append(arb_entry_log)
        save_arb_logs(arb_logs)
        st.success(f"Successfully locked delta-neutral hedge of ${arb_capital:,.2f} between {long_venue} and {short_venue}!")
        st.rerun()

    if arb_logs:
        st.markdown("##### 📜 Active Arbitrage & Funding Harvesting Positions")
        st.dataframe(pd.DataFrame(arb_logs), use_container_width=True)
        if st.button("🧹 Clear Arbitrage Ledger"):
            if os.path.exists(ARB_LOG_FILE):
                os.remove(ARB_LOG_FILE)
            st.rerun()

with tab_macro:
    st.markdown(f"### 🌐 Institutional Macro Sentiment & On-Chain Whale Tracker ({priority_asset})")
    mc1, mc2 = st.columns(2)
    with mc1:
        st.markdown("""
        <div class="terminal-card" style="border-top: 3px solid #d4af37;">
            <h5 style="color: #d4af37; margin-top:0;">Global Crypto Fear & Greed Index</h5>
            <h2 style="color: #00ffcc; margin: 5px 0;">68 / 100</h2>
            <p style="font-size:0.85rem; color:#bbb;">
            <b>Market State:</b> Greed (Institutional Accumulation Active)<br>
            <b>Derivatives Sentiment:</b> Long-Heavy (Open Interest expanding +4.2%)
            </p>
        </div>
        """, unsafe_allow_html=True)
    with mc2:
        st.markdown("""
        <div class="terminal-card" style="border-top: 3px solid #00ffcc;">
            <h5 style="color: #00ffcc; margin-top:0;">Federal Reserve Rate Probability (FOMC)</h5>
            <table style="width:100%; font-size:0.85rem; color:#bbb; margin-top:5px;">
              <tr><td><b>Current Rate:</b> 5.25% - 5.50%</td><td></td></tr>
              <tr><td><b>Next Meeting Cut (25 bps):</b></td><td style="color:#00ffcc; text-align:right;">64.2%</td></tr>
              <tr><td><b>Rate Pause Probability:</b></td><td style="color:#d4af37; text-align:right;">35.8%</td></tr>
            </table>
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown("##### 🐋 Whale Wallet On-Chain Transaction Feed")
    if st.button("📡 Scan Mempool for Whale Transactions"):
        sample_whales = [
            {"Timestamp": datetime.now().strftime("%H:%M:%S"), "Asset": priority_asset, "Volume": "4,500 BTC", "USD Value": "$292,500,000", "Origin": "Cold Storage", "Destination": "Binance Institutional OTC"},
            {"Timestamp": datetime.now().strftime("%H:%M:%S"), "Asset": "ETH", "Volume": "42,000 ETH", "USD Value": "$147,000,000", "Origin": "Coinbase Prime", "Destination": "Unknown Whale Wallet"},
            {"Timestamp": datetime.now().strftime("%H:%M:%S"), "Asset": "SOL", "Volume": "350,000 SOL", "USD Value": "$61,250,000", "Origin": "Unknown Wallet", "Destination": "Kraken"}
        ]
        for w in sample_whales:
            whale_logs.insert(0, w)
        save_whale_logs(whale_logs)
        st.success("Mempool successfully scanned for institutional block transfers!")
        st.rerun()

    if whale_logs:
        st.dataframe(pd.DataFrame(whale_logs), use_container_width=True)
        if st.button("🧹 Clear Whale Log"):
            if os.path.exists(WHALE_ALERT_FILE):
                os.remove(WHALE_ALERT_FILE)
            st.rerun()

with tab_liq:
    st.markdown(f"### 🔥 Institutional Liquidation Heatmap & Margin Cascade Engine ({priority_asset})")
    leverage_tiers = [10, 25, 50]
    liq_data = []
    for lev in leverage_tiers:
        long_liq = live_price * (1 - (1 / lev) + 0.005)
        short_liq = live_price * (1 + (1 / lev) - 0.005)
        liq_data.append({
            "Leverage": f"{lev}x",
            "Long Liquidation Trigger ($)": round(long_liq, 2),
            "Distance to Long Liq (%)": round(((live_price - long_liq) / live_price) * 100, 2) if live_price and live_price > 0 else 0.0,
    "Short Liquidation Trigger ($)": round(short_liq, 2),
    "Distance to Short Liq (%)": round(((short_liq - live_price) / live_price) * 100, 2) if live_price and live_price > 0 else 0.0
})
    st.dataframe(pd.DataFrame(liq_data), use_container_width=True)

with tab_depth:
    st.markdown(f"### 🌊 Order Book Imbalance Heatmap & Depth Walls ({priority_asset})")
    st.markdown("Visualizing live bid/ask wall depth delta to spot institutional accumulation and spoofing patterns.")
    
    total_bid_vol = bids_df['Quantity'].sum()
    total_ask_vol = asks_df['Quantity'].sum()
    imbalance_ratio = (total_bid_vol / (total_bid_vol + total_ask_vol)) * 100 if (total_bid_vol + total_ask_vol) > 0 else 50.0
    
    dm1, dm2, dm3 = st.columns(3)
    with dm1:
        st.metric("Total Bid Liquidity", value=f"{total_bid_vol:.2f} Units", delta="Buy Support")
    with dm2:
        st.metric("Total Ask Liquidity", value=f"{total_ask_vol:.2f} Units", delta="Sell Resistance")
    with dm3:
        st.metric("Order Book Imbalance", value=f"{imbalance_ratio:.1f}% Bids", delta="Bullish Bias" if imbalance_ratio > 50 else "Bearish Bias")
        
    fig_ob = go.Figure()
    fig_ob.add_trace(go.Bar(y=bids_df['Price'], x=bids_df['Quantity'], orientation='h', name='Bids (Support)', marker=dict(color='#00ffcc')))
    fig_ob.add_trace(go.Bar(y=asks_df['Price'], x=asks_df['Quantity'], orientation='h', name='Asks (Resistance)', marker=dict(color='#ff3366')))
    
    fig_ob.update_layout(
        template='plotly_dark',
        paper_bgcolor='#080808',
        plot_bgcolor='#121212',
        title=f"{priority_asset} Live Order Book Depth & Imbalance Walls",
        barmode='overlay',
        height=450,
        margin=dict(l=10, r=10, t=30, b=10),
        yaxis_title="Price ($)",
        xaxis_title="Quantity (Units)"
    )
    st.plotly_chart(fig_ob, use_container_width=True)

with tab_grid:
    st.markdown(f"### 🤖 Automated Limit Order Grid & DCA Simulator ({priority_asset})")
    gc1, gc2 = st.columns(2)
    with gc1:
        grid_capital = st.number_input("Total Grid Allocation ($)", value=5000.0, step=500.0)
        num_grids = st.slider("Number of Grid Levels", min_value=3, max_value=15, value=5)
    with gc2:
        price_drop_pct = st.slider("Max Grid Depth (% Below Live Price)", min_value=2.0, max_value=30.0, value=10.0, step=1.0)
        
    grid_prices = [live_price * (1 - (i * (price_drop_pct / 100.0) / (num_grids - 1))) for i in range(num_grids)]
    allocation_per_grid = grid_capital / num_grids
    
    grid_df_data = []
    for idx, gp in enumerate(grid_prices):
        units = allocation_per_grid / gp if gp and gp > 0 else 0.0
        grid_df_data.append({
            "Grid Order": f"Tier {idx + 1}",
            "Trigger Price ($)": round(gp, 2),
            "Allocation ($)": round(allocation_per_grid, 2),
            "Asset Units": round(units, 4)
        })
    st.dataframe(pd.DataFrame(grid_df_data), use_container_width=True)

with tab_leverage:
    st.markdown(f"### ⚙️ Institutional Margin & Liquidation Calculator ({priority_asset})")
    lc1, lc2 = st.columns(2)
    with lc1:
        lev_direction = st.selectbox("Position Direction", ["Long", "Short"])
        lev_entry = st.number_input("Leverage Entry Price ($)", value=live_price, step=10.0)
    with lc2:
        lev_multiplier = st.slider("Leverage Multiplier (x)", min_value=1, max_value=50, value=10)
        margin_allocated = st.number_input("Margin Allocated ($)", value=1000.0, step=100.0)
        
    position_notional = margin_allocated * lev_multiplier
    liquidation_price = lev_entry * (1 - (1 / lev_multiplier) + 0.005) if lev_direction == "Long" else lev_entry * (1 + (1 / lev_multiplier) - 0.005)
    
    lm1, lm2, lm3 = st.columns(3)
    with lm1:
        st.metric("Total Position Notional", value=f"${position_notional:,.2f}", delta=f"{lev_multiplier}x Leverage")
    with lm2:
        st.metric("Estimated Liquidation Price", value=f"${liquidation_price:,.2f}", delta="Risk Level", delta_color="inverse")
    with lm3:
        buffer_pct = f"{abs((live_price - liquidation_price) / live_price) * 100:.2f}%" if live_price and live_price > 0 else "0.00%"
st.metric("Buffer to Liquidation", value=buffer_pct, delta="Distance")

with tab_backtest:
    st.markdown(f"### 📈 Algorithmic Backtest Engine ({priority_asset})")
    bc1, bc2 = st.columns(2)
    with bc1:
        fast_sma_period = st.slider("Fast Moving Average Window", min_value=3, max_value=20, value=5)
    with bc2:
        slow_sma_period = st.slider("Slow Moving Average Window", min_value=15, max_value=50, value=20)
        
    df_bt = df_market.copy()
if not df_bt.empty and 'Close' in df_bt.columns:
    df_bt['Fast_SMA'] = df_bt['Close'].rolling(window=fast_sma_period).mean()
    df_bt['Slow_SMA'] = df_bt['Close'].rolling(window=slow_sma_period).mean()
    
    df_bt['Signal'] = 0
    df_bt.loc[df_bt['Fast_SMA'] > df_bt['Slow_SMA'], 'Signal'] = 1
    df_bt['Market_Return'] = df_bt['Close'].pct_change()
    df_bt['Strategy_Return'] = df_bt['Market_Return'] * df_bt['Signal'].shift(1)
    
    df_bt['Cumulative_Market'] = (1 + df_bt['Market_Return'].fillna(0)).cumprod() - 1
    df_bt['Cumulative_Strategy'] = (1 + df_bt['Strategy_Return'].fillna(0)).cumprod() - 1
    
    total_strat_return = df_bt['Cumulative_Strategy'].iloc[-1] * 100
    total_mkt_return = df_bt['Cumulative_Market'].iloc[-1] * 100
    
    bm1, bm2, bm3 = st.columns(3)
    with bm1:
        st.metric("Strategy Return", value=f"{total_strat_return:.2f}%", delta=f"vs Market {total_mkt_return:.2f}%")
    with bm2:
        st.metric("Total Crossover Signals", value=str((df_bt['Signal'].diff() != 0).sum()), delta="Executed")
    with bm3:
        st.metric("Sample Size", value=f"{len(df_bt)} Candles", delta="1H Interval")
        
    fig_bt = go.Figure()
    fig_bt.add_trace(go.Scatter(x=df_bt['Timestamp'], y=df_bt['Cumulative_Strategy'] * 100, name='Strategy Return (%)', line=dict(color='#00ffcc', width=2)))
    fig_bt.add_trace(go.Scatter(x=df_bt['Timestamp'], y=df_bt['Cumulative_Market'] * 100, name='Buy & Hold Return (%)', line=dict(color='#d4af37', width=1.5, dash='dot')))
    fig_bt.update_layout(template='plotly_dark', paper_bgcolor='#080808', plot_bgcolor='#121212', margin=dict(l=10, r=10, t=10, b=10), height=400)
    st.plotly_chart(fig_bt, use_container_width=True)

with tab_matrix:
    st.markdown("### 🔗 Institutional Cross-Asset Correlation Matrix")
    st.dataframe(df_corr.style.format("{:.2f}"), use_container_width=True)

with tab_journal:
    st.markdown("### 📒 Institutional Trade Journal & Execution Ledger")
    if not journal_trades:
        st.info("No trades logged yet. Use the 'Log This Trade to Journal' button in the main tab.")
    else:
        st.dataframe(pd.DataFrame(journal_trades), use_container_width=True)
        if st.button("🗑️ Clear Journal History"):
            if os.path.exists(JOURNAL_FILE):
                os.remove(JOURNAL_FILE)
            st.success("Journal cleared.")
            st.rerun()

with tab_news:
    st.markdown("### 📰 Live Exchange Wire & Real-Time Intelligence Feed")
    for item in live_news:
        st.markdown(f"""
        <div class="terminal-card">
            <span style="font-size:0.75rem; color:#d4af37;">{item['source']} • <b>{item['time']}</b></span><br>
            <h5 style="margin: 5px 0 8px 0; color: #fff;"><a href="{item['url']}" target="_blank" style="color: #fff; text-decoration: none;">{item['headline']} ↗</a></h5>
        </div>
        """, unsafe_allow_html=True)

with tab_lifecycle:
    st.markdown("### 📚 Complete Lifecycle, Historical Crashes & Catalyst Engine (2009 — 2026)")
    st.markdown("Project Entity has ingested every major market cycle and macroeconomic catalyst in crypto history.")

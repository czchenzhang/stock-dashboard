import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import time
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. Page Configuration
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Pro TradeView + Paper Trading",
    page_icon="📈",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .stMetric { background-color: #262730; padding: 15px; border-radius: 10px; }
    .stButton>button { width: 100%; border-radius: 5px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Session State
# -----------------------------------------------------------------------------
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.00
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'transactions' not in st.session_state:
    st.session_state.transactions = []

# -----------------------------------------------------------------------------
# 3. Sidebar & Settings
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ Settings")
ticker_symbol = st.sidebar.text_input("Symbol", "AAPL").upper()
time_period = st.sidebar.selectbox("Time Frame", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)
chart_interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Account Info")
st.sidebar.metric("Cash Balance", f"${st.session_state.balance:,.2f}")

if st.sidebar.button("Reset Account"):
    st.session_state.balance = 100000.00
    st.session_state.portfolio = {}
    st.session_state.transactions = []
    st.rerun()

# -----------------------------------------------------------------------------
# 4. Data Functions
# -----------------------------------------------------------------------------
def get_data(symbol, period, interval):
    try:
        df = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
        # Fix for new yfinance version returning MultiIndex
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        df.reset_index(inplace=True)
        df.columns = [c.capitalize() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error: {e}")
        return pd.DataFrame()

def execute_trade(action, symbol, price, qty):
    cost = price * qty
    if action == "BUY":
        if st.session_state.balance >= cost:
            st.session_state.balance -= cost
            if symbol in st.session_state.portfolio:
                current_qty = st.session_state.portfolio[symbol]['qty']
                current_avg = st.session_state.portfolio[symbol]['avg_price']
                new_avg = ((current_avg * current_qty) + cost) / (current_qty + qty)
                st.session_state.portfolio[symbol]['qty'] += qty
                st.session_state.portfolio[symbol]['avg_price'] = new_avg
            else:
                st.session_state.portfolio[symbol] = {'qty': qty, 'avg_price': price}
            
            st.session_state.transactions.append({
                "Date": datetime.now(), "Type": "BUY", "Symbol": symbol, 
                "Price": price, "Qty": qty, "Total": -cost
            })
            st.success(f"Bought {qty} {symbol} @ ${price:.2f}")
        else:
            st.error("❌ Insufficient Funds!")

    elif action == "SELL":
        if symbol in st.session_state.portfolio and st.session_state.portfolio[symbol]['qty'] >= qty:
            revenue = price * qty
            st.session_state.balance += revenue
            st.session_state.portfolio[symbol]['qty'] -= qty
            if st.session_state.portfolio[symbol]['qty'] == 0:
                del st.session_state.portfolio[symbol]
            
            st.session_state.transactions.append({
                "Date": datetime.now(), "Type": "SELL", "Symbol": symbol, 
                "Price": price, "Qty": qty, "Total": revenue
            })
            st.success(f"Sold {qty} {symbol} @ ${price:.2f}")
        else:
            st.error("❌ Not enough shares!")

# -----------------------------------------------------------------------------
# 5. Main Dashboard
# -----------------------------------------------------------------------------
st.title(f"📈 {ticker_symbol} Live Market")

df = get_data(ticker_symbol, time_period, chart_interval)

if not df.empty:
    latest_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2] if len(df) > 1 else latest_price
    price_change = latest_price - prev_price
    pct_change = (price_change / prev_price) * 100

    m1, m2, m3 = st.columns(3)
    m1.metric("Price", f"${latest_price:.2f}", f"{price_change:.2f} ({pct_change:.2f}%)")
    m2.metric("High", f"${df['High'].iloc[-1]:.2f}")
    m3.metric("Low", f"${df['Low'].iloc[-1]:.2f}")

    fig = go.Figure(data=[go.Candlestick(
        x=df.iloc[:, 0], open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'], name=ticker_symbol
    )])
    fig.update_layout(height=500, margin=dict(l=0, r=0, t=0, b=0), template="plotly_dark")
    st.plotly_chart(fig, use_container_width=True)

    # Trading Panel
    st.markdown("### ⚡ Quick Trade")
    col_buy, col_sell = st.columns(2)

    with col_buy:
        buy_qty = st.number_input("Buy Qty", min_value=1, value=1, key="buy_qty")
        if st.button("🟢 BUY", type="primary"):
            execute_trade("BUY", ticker_symbol, latest_price, buy_qty)

    with col_sell:
        owned_qty = st.session_state.portfolio.get(ticker_symbol, {}).get('qty', 0)
        st.info(f"Owned: {owned_qty}")
        sell_qty = st.number_input("Sell Qty", min_value=1, value=1, key="sell_qty")
        if st.button("🔴 SELL", type="secondary"):
            execute_trade("SELL", ticker_symbol, latest_price, sell_qty)

else:
    st.warning("Data not available.")

# -----------------------------------------------------------------------------
# 6. Portfolio
# -----------------------------------------------------------------------------
st.markdown("---")
tab1, tab2 = st.tabs(["💼 Portfolio", "📝 History"])

with tab1:
    if st.session_state.portfolio:
        portfolio_data = []
        total_equity = 0
        
        for sym, data in st.session_state.portfolio.items():
            # Use current price if viewing that stock, otherwise use avg_price
            curr_val = latest_price if sym == ticker_symbol else data['avg_price']
            market_value = curr_val * data['qty']
            total_equity += market_value
            pnl = market_value - (data['avg_price'] * data['qty'])
            
            portfolio_data.append({
                "Symbol": sym,
                "Shares": data['qty'],
                "Avg Price": f"${data['avg_price']:.2f}",
                "Current Price": f"${curr_val:.2f}",
                "Market Value": f"${market_value:.2f}",
                "Unrealized P/L": f"${pnl:.2f}"
            })
            
        st.dataframe(pd.DataFrame(portfolio_data), use_container_width=True)
        st.metric("Total Net Worth", f"${st.session_state.balance + total_equity:,.2f}")
    else:
        st.info("No open positions.")

with tab2:
    if st.session_state.transactions:
        st.dataframe(pd.DataFrame(st.session_state.transactions).sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.info("No trades yet.")
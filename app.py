import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import time
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. Page Config & CSS (The Pro Design)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade Terminal",
    page_icon="⚡",
    layout="wide"
)

st.markdown("""
<style>
    /* Global Dark Theme */
    .stApp { background-color: #0E1117; font-family: 'Inter', sans-serif; }
    [data-testid="stSidebar"] { background-color: #161B22; border-right: 1px solid #30363D; }

    /* Metrics & Tables */
    div[data-testid="stMetric"] {
        background-color: #21262D;
        border: 1px solid #30363D;
        padding: 15px;
        border-radius: 8px;
    }
    [data-testid="stDataFrame"] { border: 1px solid #30363D; border-radius: 8px; }
    
    /* Buttons */
    button[kind="primary"] {
        background-color: #238636 !important;
        border: 1px solid #2EA043 !important;
        color: white !important;
    }
    button[kind="secondary"] {
        background-color: #DA3633 !important;
        border: 1px solid #F85149 !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Session State Setup
# -----------------------------------------------------------------------------
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.00
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'transactions' not in st.session_state:
    st.session_state.transactions = []

# -----------------------------------------------------------------------------
# 3. Sidebar Controls
# -----------------------------------------------------------------------------
st.sidebar.title("⚡ ProTrade")
ticker_symbol = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()
time_period = st.sidebar.selectbox("Time Period", ["1d", "5d", "1mo", "6mo"], index=0)
chart_interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "1h", "1d"], index=0)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Account")
# Display balance rounded strictly to 2 decimals
st.sidebar.metric("Cash Balance", f"${st.session_state.balance:,.2f}")

if st.sidebar.button("🔄 Reset Account"):
    st.session_state.balance = 100000.00
    st.session_state.portfolio = {}
    st.session_state.transactions = []
    st.rerun()

# -----------------------------------------------------------------------------
# 4. Robust Data Functions (FIXED)
# -----------------------------------------------------------------------------
def get_data(symbol, period, interval):
    """Fetches data for the Main Chart."""
    try:
        df = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        df.reset_index(inplace=True)
        df.columns = [c.capitalize() for c in df.columns]
        return df
    except Exception as e:
        return pd.DataFrame()

def get_current_price(symbol):
    """Helper to get a single float price for a stock right now."""
    try:
        # We fetch 1 day of data to get the absolute latest close
        df = yf.download(tickers=symbol, period="1d", interval="1m", progress=False)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if not df.empty:
            return round(df['Close'].iloc[-1], 2)
        return 0.0
    except:
        return 0.0

def execute_trade(action, symbol, price, qty):
    """
    Executes trade with STRICT rounding to 2 decimals 
    to prevent floating point errors (e.g., 99999.99999).
    """
    price = round(price, 2) # Force price to 2 decimals
    cost = round(price * qty, 2)
    
    if action == "BUY":
        if st.session_state.balance >= cost:
            # Deduct Cash
            st.session_state.balance = round(st.session_state.balance - cost, 2)
            
            # Update Portfolio
            if symbol in st.session_state.portfolio:
                old_qty = st.session_state.portfolio[symbol]['qty']
                old_avg = st.session_state.portfolio[symbol]['avg_price']
                
                # Calculate new weighted average
                # (Old Total Val + New Cost) / Total Qty
                new_avg = ((old_avg * old_qty) + cost) / (old_qty + qty)
                
                st.session_state.portfolio[symbol]['qty'] += qty
                st.session_state.portfolio[symbol]['avg_price'] = round(new_avg, 2)
            else:
                st.session_state.portfolio[symbol] = {'qty': qty, 'avg_price': price}
            
            # Log
            st.session_state.transactions.append({
                "Date": datetime.now(), "Type": "BUY", "Symbol": symbol, 
                "Price": price, "Qty": qty, "Total": -cost
            })
            st.success(f"Bought {qty} {symbol} @ ${price}")
        else:
            st.error("❌ Insufficient Funds")
            
    elif action == "SELL":
        if symbol in st.session_state.portfolio and st.session_state.portfolio[symbol]['qty'] >= qty:
            # Add Cash
            st.session_state.balance = round(st.session_state.balance + cost, 2)
            
            # Update Portfolio
            st.session_state.portfolio[symbol]['qty'] -= qty
            
            # Remove if 0
            if st.session_state.portfolio[symbol]['qty'] == 0:
                del st.session_state.portfolio[symbol]
            
            # Log
            st.session_state.transactions.append({
                "Date": datetime.now(), "Type": "SELL", "Symbol": symbol, 
                "Price": price, "Qty": qty, "Total": cost
            })
            st.success(f"Sold {qty} {symbol} @ ${price}")
        else:
            st.error("❌ Insufficient Shares")

# -----------------------------------------------------------------------------
# 5. Main Dashboard
# -----------------------------------------------------------------------------
st.title(f"{ticker_symbol} Market Terminal")

# 1. Get Data
df = get_data(ticker_symbol, time_period, chart_interval)

if not df.empty:
    latest_close = round(df['Close'].iloc[-1], 2)
    prev_close = df['Close'].iloc[-2] if len(df) > 1 else latest_close
    diff = round(latest_close - prev_close, 2)
    pct = round((diff / prev_close) * 100, 2)

    # 2. Metrics
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Price", f"${latest_close}", f"{diff} ({pct}%)")
    c2.metric("High", f"${df['High'].iloc[-1]:.2f}")
    c3.metric("Low", f"${df['Low'].iloc[-1]:.2f}")
    c4.metric("Volume", f"{df['Volume'].iloc[-1]:,}")

    # 3. Chart
    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=df.iloc[:, 0], open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'], name=ticker_symbol
    ))
    fig.update_layout(
        height=500, margin=dict(t=20, b=0, l=0, r=0),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=False, color='#8B949E'),
        yaxis=dict(showgrid=True, gridcolor='#30363D', color='#8B949E'),
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    # 4. Trading Panel
    st.markdown("### ⚡ Quick Trade")
    tc1, tc2 = st.columns(2)
    
    with tc1:
        st.caption("Buy Stock")
        b_qty = st.number_input("Qty", 1, 10000, 1, key="buy_btn")
        if st.button("BUY", type="primary", use_container_width=True):
            execute_trade("BUY", ticker_symbol, latest_close, b_qty)
            
    with tc2:
        st.caption("Sell Stock")
        s_qty = st.number_input("Qty", 1, 10000, 1, key="sell_btn")
        if st.button("SELL", type="secondary", use_container_width=True):
            execute_trade("SELL", ticker_symbol, latest_close, s_qty)

else:
    st.warning("Ticker not found or market data unavailable.")

# -----------------------------------------------------------------------------
# 6. Portfolio Logic (FIXED VALUATION)
# -----------------------------------------------------------------------------
st.markdown("---")
tab_p, tab_h = st.tabs(["💼 Portfolio", "📝 History"])

with tab_p:
    if st.session_state.portfolio:
        # To fix the "Math Error", we need REAL TIME prices for EVERYTHING in the portfolio
        # not just the active stock.
        
        portfolio_tickers = list(st.session_state.portfolio.keys())
        
        # Batch fetch latest prices for portfolio to ensure Net Worth is accurate
        # If only 1 ticker in portfolio, use current data, else fetch batch
        live_prices = {}
        
        if len(portfolio_tickers) > 0:
            try:
                # Quick fetch of 1 minute data for all held stocks
                p_data = yf.download(portfolio_tickers, period="1d", interval="1m", progress=False)['Close']
                
                # Handle case where p_data is Series (1 stock) or DataFrame (multiple)
                if isinstance(p_data, pd.Series):
                    live_prices[portfolio_tickers[0]] = round(p_data.iloc[-1], 2)
                else:
                    for t in portfolio_tickers:
                        # Check if column exists (sometimes yfinance drops invalid tickers)
                        if t in p_data.columns:
                            live_prices[t] = round(p_data[t].iloc[-1], 2)
                        else:
                            # Fallback to avg price if fetch fails
                            live_prices[t] = st.session_state.portfolio[t]['avg_price']
            except:
                pass

        # Build Table
        rows = []
        total_equity = 0.0
        
        for sym, data in st.session_state.portfolio.items():
            # Get live price from our batch fetch, or fallback to current screen if matches
            current_price = live_prices.get(sym, data['avg_price'])
            if sym == ticker_symbol: current_price = latest_close # Use most fresh data for active symbol
            
            qty = data['qty']
            avg_price = data['avg_price']
            
            market_val = round(current_price * qty, 2)
            total_equity += market_val
            
            unrealized_pl = round(market_val - (avg_price * qty), 2)
            
            rows.append({
                "Symbol": sym,
                "Qty": qty,
                "Avg Cost": f"${avg_price:.2f}",
                "Current Price": f"${current_price:.2f}",
                "Market Value": f"${market_val:,.2f}",
                "Unrealized P/L": f"${unrealized_pl:,.2f}"
            })
            
        # Final Net Worth Calculation
        net_worth = round(st.session_state.balance + total_equity, 2)
        
        st.metric("Total Net Worth", f"${net_worth:,.2f}")
        st.dataframe(pd.DataFrame(rows), use_container_width=True)
        
    else:
        st.info("Portfolio is empty. Buy stocks to see them here.")

with tab_h:
    if st.session_state.transactions:
        hist_df = pd.DataFrame(st.session_state.transactions)
        st.dataframe(hist_df.sort_values(by="Date", ascending=False), use_container_width=True)
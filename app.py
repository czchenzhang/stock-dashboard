import streamlit as st
import yfinance as yf
import plotly.graph_objs as go
import pandas as pd
import time
from datetime import datetime

# -----------------------------------------------------------------------------
# 1. Page Config & Custom Design (Figma Style)
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="ProTrade Platform",
    page_icon="⚡",
    layout="wide"
)

# Inject Custom CSS for the "Dark Glassmorphism" Look
st.markdown("""
<style>
    /* Main Background */
    .stApp {
        background-color: #0E1117;
        font-family: 'Inter', sans-serif;
    }

    /* Sidebar Background */
    [data-testid="stSidebar"] {
        background-color: #161B22;
        border-right: 1px solid #30363D;
    }

    /* Metric Cards Styling */
    div[data-testid="stMetric"] {
        background-color: #21262D;
        border: 1px solid #30363D;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
    div[data-testid="stMetricLabel"] {
        font-size: 14px;
        color: #8B949E;
    }
    div[data-testid="stMetricValue"] {
        color: #FFFFFF;
    }

    /* Buttons Styling */
    button[kind="primary"] {
        background-color: #238636;
        border: none;
        color: white;
        font-weight: bold;
        transition: 0.2s;
    }
    button[kind="primary"]:hover {
        background-color: #2EA043;
    }
    
    button[kind="secondary"] {
        background-color: #DA3633;
        border: none;
        color: white;
        font-weight: bold;
    }
    button[kind="secondary"]:hover {
        background-color: #F85149;
    }

    /* Tabs Styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 20px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        background-color: transparent;
        color: #8B949E;
    }
    .stTabs [aria-selected="true"] {
        color: #58A6FF;
        border-bottom: 2px solid #58A6FF;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Session State (Paper Trading Logic)
# -----------------------------------------------------------------------------
if 'balance' not in st.session_state:
    st.session_state.balance = 100000.00
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = {}
if 'transactions' not in st.session_state:
    st.session_state.transactions = []

# -----------------------------------------------------------------------------
# 3. Sidebar Inputs
# -----------------------------------------------------------------------------
st.sidebar.title("⚡ ProTrade")
ticker_symbol = st.sidebar.text_input("Ticker Symbol", "AAPL").upper()
time_period = st.sidebar.selectbox("Time Period", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=2)
chart_interval = st.sidebar.selectbox("Chart Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=4)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Account")
st.sidebar.metric("Cash Balance", f"${st.session_state.balance:,.2f}")

if st.sidebar.button("🔄 Reset Account"):
    st.session_state.balance = 100000.00
    st.session_state.portfolio = {}
    st.session_state.transactions = []
    st.rerun()

# -----------------------------------------------------------------------------
# 4. Helper Functions
# -----------------------------------------------------------------------------
def get_data(symbol, period, interval):
    try:
        df = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
        
        # Fix for yfinance MultiIndex issue
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        df.reset_index(inplace=True)
        df.columns = [c.capitalize() for c in df.columns]
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

def execute_trade(action, symbol, price, qty):
    cost = price * qty
    if action == "BUY":
        if st.session_state.balance >= cost:
            st.session_state.balance -= cost
            
            # Portfolio Logic (Weighted Average)
            if symbol in st.session_state.portfolio:
                current_qty = st.session_state.portfolio[symbol]['qty']
                current_avg = st.session_state.portfolio[symbol]['avg_price']
                new_avg = ((current_avg * current_qty) + cost) / (current_qty + qty)
                st.session_state.portfolio[symbol]['qty'] += qty
                st.session_state.portfolio[symbol]['avg_price'] = new_avg
            else:
                st.session_state.portfolio[symbol] = {'qty': qty, 'avg_price': price}
                
            # Log Transaction
            st.session_state.transactions.append({
                "Date": datetime.now(), "Type": "BUY", "Symbol": symbol, 
                "Price": price, "Qty": qty, "Total": -cost
            })
            st.success(f"Bought {qty} {symbol} @ ${price:.2f}")
        else:
            st.error("❌ Insufficient Funds")
            
    elif action == "SELL":
        if symbol in st.session_state.portfolio and st.session_state.portfolio[symbol]['qty'] >= qty:
            revenue = price * qty
            st.session_state.balance += revenue
            
            # Update Portfolio
            st.session_state.portfolio[symbol]['qty'] -= qty
            if st.session_state.portfolio[symbol]['qty'] == 0:
                del st.session_state.portfolio[symbol]
                
            # Log Transaction
            st.session_state.transactions.append({
                "Date": datetime.now(), "Type": "SELL", "Symbol": symbol, 
                "Price": price, "Qty": qty, "Total": revenue
            })
            st.success(f"Sold {qty} {symbol} @ ${price:.2f}")
        else:
            st.error("❌ Insufficient Shares")

# -----------------------------------------------------------------------------
# 5. Main Dashboard Layout
# -----------------------------------------------------------------------------
st.title(f"{ticker_symbol} Market Data")

# Fetch Data
df = get_data(ticker_symbol, time_period, chart_interval)

if not df.empty:
    # Metrics Calculation
    latest_price = df['Close'].iloc[-1]
    prev_price = df['Close'].iloc[-2] if len(df) > 1 else latest_price
    price_change = latest_price - prev_price
    pct_change = (price_change / prev_price) * 100

    # Display Metrics
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Current Price", f"${latest_price:.2f}", f"{price_change:.2f} ({pct_change:.2f}%)")
    col2.metric("High", f"${df['High'].iloc[-1]:.2f}")
    col3.metric("Low", f"${df['Low'].iloc[-1]:.2f}")
    col4.metric("Volume", f"{df['Volume'].iloc[-1]:,}")

    # -------------------------------------------------------------------------
    # Optimized Plotly Chart (Dark Theme)
    # -------------------------------------------------------------------------
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=df.iloc[:, 0], 
        open=df['Open'], high=df['High'], 
        low=df['Low'], close=df['Close'], 
        name=ticker_symbol
    ))

    # Chart Layout Styling
    fig.update_layout(
        height=550,
        margin=dict(l=0, r=0, t=20, b=0),
        paper_bgcolor='rgba(0,0,0,0)',  # Transparent
        plot_bgcolor='rgba(0,0,0,0)',   # Transparent
        xaxis=dict(
            showgrid=False, 
            color='#8B949E',
            rangeslider=dict(visible=False)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor='#30363D', 
            color='#8B949E'
        ),
        template="plotly_dark"
    )
    st.plotly_chart(fig, use_container_width=True)

    # -------------------------------------------------------------------------
    # Trading Interface
    # -------------------------------------------------------------------------
    st.markdown("### ⚡ Trade Actions")
    t_col1, t_col2 = st.columns(2)
    
    with t_col1:
        st.caption("Buy Stock")
        buy_qty = st.number_input("Quantity", min_value=1, value=1, key="buy_qty")
        if st.button("🟢 BUY", type="primary", use_container_width=True):
            execute_trade("BUY", ticker_symbol, latest_price, buy_qty)
            
    with t_col2:
        st.caption("Sell Stock")
        # Show owned quantity helper
        owned = st.session_state.portfolio.get(ticker_symbol, {}).get('qty', 0)
        st.markdown(f"**Owned:** {owned} shares")
        sell_qty = st.number_input("Quantity", min_value=1, value=1, key="sell_qty")
        if st.button("🔴 SELL", type="secondary", use_container_width=True):
            execute_trade("SELL", ticker_symbol, latest_price, sell_qty)

else:
    st.warning("No data found. Market might be closed or ticker is invalid.")

# -----------------------------------------------------------------------------
# 6. Portfolio & History Tabs
# -----------------------------------------------------------------------------
st.markdown("---")
tab1, tab2 = st.tabs(["💼 Portfolio", "📝 Transaction History"])

with tab1:
    if st.session_state.portfolio:
        # Prepare Data for Table
        portfolio_items = []
        total_equity = 0
        
        for sym, data in st.session_state.portfolio.items():
            # If we are viewing the stock, use live price, else use avg cost (simplified)
            current_val = latest_price if sym == ticker_symbol else data['avg_price']
            market_val = current_val * data['qty']
            total_equity += market_val
            pnl = market_val - (data['avg_price'] * data['qty'])
            
            portfolio_items.append({
                "Symbol": sym,
                "Shares": data['qty'],
                "Avg Price": f"${data['avg_price']:.2f}",
                "Current Price": f"${current_val:.2f}",
                "Market Value": f"${market_val:.2f}",
                "Unrealized P/L": f"${pnl:.2f}"
            })
        
        # Display Summary
        st.metric("Total Net Worth", f"${st.session_state.balance + total_equity:,.2f}")
        st.dataframe(pd.DataFrame(portfolio_items), use_container_width=True)
    else:
        st.info("Your portfolio is empty.")

with tab2:
    if st.session_state.transactions:
        hist_df = pd.DataFrame(st.session_state.transactions)
        st.dataframe(hist_df.sort_values(by="Date", ascending=False), use_container_width=True)
    else:
        st.info("No transactions yet.")
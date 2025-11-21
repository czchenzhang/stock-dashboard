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
    page_title="Pro TradeView",
    page_icon="📈",
    layout="wide"
)

# Custom CSS to make it look more like a trading platform
st.markdown("""
<style>
    .stApp { background-color: #0e1117; color: white; }
    .stMetric { background-color: #262730; padding: 15px; border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. Sidebar & Inputs
# -----------------------------------------------------------------------------
st.sidebar.title("⚙️ Settings")
ticker_symbol = st.sidebar.text_input("Symbol", "AAPL").upper()
time_period = st.sidebar.selectbox("Time Frame", ["1d", "5d", "1mo", "3mo", "6mo", "1y"], index=0)
chart_interval = st.sidebar.selectbox("Interval", ["1m", "5m", "15m", "30m", "1h", "1d"], index=0)

# Auto-Refresh Logic
st.sidebar.markdown("---")
live_mode = st.sidebar.checkbox("🔴 Live Mode (Auto-Refresh)", value=False)
refresh_rate = st.sidebar.slider("Refresh rate (seconds)", 2, 60, 10)

# -----------------------------------------------------------------------------
# 3. Data Functions
# -----------------------------------------------------------------------------
def get_data(symbol, period, interval):
    try:
        # Fetch data
        df = yf.download(tickers=symbol, period=period, interval=interval, progress=False)
        
        # Reset index to ensure Date/Datetime is a column
        df.reset_index(inplace=True)
        
        # Handle MultiIndex columns (yfinance update fix)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Rename columns to standard format if needed
        df.columns = [c.capitalize() for c in df.columns]
        
        return df
    except Exception as e:
        st.error(f"Error fetching data: {e}")
        return pd.DataFrame()

# -----------------------------------------------------------------------------
# 4. Main Dashboard
# -----------------------------------------------------------------------------
st.title(f"📈 {ticker_symbol} Market Overview")

# Create a placeholder for the main content so we can update it in Live Mode
placeholder = st.empty()

# Define the rendering function
def render_dashboard():
    with placeholder.container():
        # Fetch Data
        df = get_data(ticker_symbol, time_period, chart_interval)

        if df.empty:
            st.warning("No data found. Is the market open? Check the symbol.")
            return

        # Calculate Metrics
        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest
        
        price = latest['Close']
        change = price - prev['Close']
        pct_change = (change / prev['Close']) * 100
        
        # Color logic for metrics
        delta_color = "normal" # Streamlit handles green/red automatically for deltas

        # Display Metrics Row
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"${price:.2f}", f"{change:.2f} ({pct_change:.2f}%)", delta_color=delta_color)
        c2.metric("High", f"${latest['High']:.2f}")
        c3.metric("Low", f"${latest['Low']:.2f}")
        c4.metric("Volume", f"{latest['Volume']:,}")

        # Plotly Candle Stick Chart
        fig = go.Figure()

        # Candlestick Trace
        fig.add_trace(go.Candlestick(
            x=df.iloc[:, 0], # First column is usually Date/Datetime
            open=df['Open'],
            high=df['High'],
            low=df['Low'],
            close=df['Close'],
            name=ticker_symbol
        ))

        # Add Moving Average (Example Indicator)
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        fig.add_trace(go.Scatter(
            x=df.iloc[:, 0], 
            y=df['SMA20'], 
            mode='lines', 
            name='SMA 20', 
            line=dict(color='orange', width=1)
        ))

        # Chart Styling
        fig.update_layout(
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            height=600,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)'
        )

        st.plotly_chart(fig, use_container_width=True)
        
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")

# -----------------------------------------------------------------------------
# 5. Execution Loop
# -----------------------------------------------------------------------------

if live_mode:
    # Loop to simulate live updates
    while True:
        render_dashboard()
        time.sleep(refresh_rate)
else:
    # Static render (Standard)
    render_dashboard()
    if st.sidebar.button("Manual Refresh"):
        st.rerun()
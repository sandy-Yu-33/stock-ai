from datetime import datetime, timedelta
import numpy as np
import pandas as pd
plotly_available = True
try:
  import plotly.graph_objects as go
except ImportError:
  plotly_available = False
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import MinMaxScaler
import streamlit as st
import yfinance as yf

# 設置頁面配置
st.set_page_config(
    page_title="Stock AI 分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 Stock AI 智慧股市分析與多因子預測系統")
st.markdown("---")

# 側邊欄配置
with st.sidebar:
  st.header("⚙️ 設定與全球市場")

  # 股票代碼輸入
  stock_symbol = st.text_input(
      "輸入股票代碼 (例: 2330, 2344, AAPL)",
      value="2330",
      placeholder="輸入股票代碼",
  )

  # 自動補上 .TW
  if stock_symbol.isdigit() and len(stock_symbol) == 4:
    stock_symbol = stock_symbol + ".TW"

  # 時間範圍選擇
  time_range = st.selectbox(
      "選擇歷史數據範圍", ["1個月", "3個月", "6個月", "1年", "2年", "5年"]
  )
  period_map = {
      "1個月": "1mo",
      "3個月": "3mo",
      "6個月": "6mo",
      "1年": "1y",
      "2年": "2y",
      "5年": "5y",
  }
  period = period_map[time_range]

  st.markdown("---")
  st.subheader("🌐 美股與國際指數參考")
  global_indices = {"標普500 (^GSPC)": "^GSPC", "那斯達克 (^IXIC)": "^IXIC"}
  for name, symbol in global_indices.items():
    try:
      g_data = yf.download(symbol, period="5d", progress=False)
      if isinstance(g_data.columns, pd.MultiIndex):
        g_data.columns = g_data.columns.droplevel(1)
      g_close = g_data["Close"].iloc[-1]
      g_prev = g_data["Close"].iloc[-2]
      g_chg = ((g_close - g_prev) / g_prev) * 100
      st.metric(name, f"{g_close:.2f}", f"{g_chg:+.2f}%")
    except:
      st.text(f"{name}: 數據載入中...")

# 主要分析邏輯
if stock_symbol:
  try:
    with st.spinner(f"正在加載 {stock_symbol} 數據與全球新聞..."):
      stock_data = yf.download(stock_symbol, period=period, progress=False)

    if stock_data.empty:
      st.error(f"❌ 無法找到股票代碼: {stock_symbol}")
    else:
      ticker = yf.Ticker(stock_symbol)
      info = ticker.info

      if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.droplevel(1)

      # 顯示基本指標
      col1, col2, col3, col4 = st.columns(4)
      current_price = float(stock_data["Close"].iloc[-1])
      prev_close = float(stock_data["Close"].iloc[-2])
      change = current_price - prev_close
      change_percent = (change / prev_close) * 100

      col1.metric("當前收盤價", f"${current_price:.2f}")
      col2.metric("日漲跌幅", f"${change:.2f}", f"{change_percent:.2f}%")
      col3.metric("最高價", f"${stock_data['High'].max():.2f}")
      col4.metric("最低價", f"${stock_data['Low'].min():.2f}")

      st.markdown("---")
      tab1, tab2, tab3, tab4 = st.tabs(
          ["📊 價格與買賣訊號", "📈 技術分析 (加粗版)", "🔮 AI 預測", "📰 即時新聞與輿情"]
      )

      # 計算均線與 RSI
      stock_data["MA20"] = stock_data["Close"].rolling(window=20).mean()
      stock_data["MA50"] = stock_data["Close"].rolling(window=50).mean()
      delta = stock_data["Close"].diff()
      gain = delta.where(delta > 0, 0).rolling(window=14).mean()
      loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
      rs = gain / loss
      stock_data["RSI"] = 100 - (100 / (1 + rs))

      # 產生買賣訊號
      stock_data["Signal"] = 0
      # 黃金交叉或 RSI 超賣買進
      stock_data.loc[
          (stock_data["MA20"] > stock_data["MA50"])
          & (stock_data["RSI"] < 40),
          "Signal",
      ] = 1
      # 死亡交叉或 RSI 超買賣出
      stock_data.loc[
          (stock_data["MA20"] < stock_data["MA50"])
          & (stock_data["RSI"] > 65),
          "Signal",
      ] = -1

      buy_signals = stock_data[stock_data["Signal"] == 1]
      sell_signals = stock_data[stock_data["Signal"] == -1]

      # 標籤 1: 價格與買賣訊號
      with tab1:
        st.subheader("🎯 智慧買賣點訊號圖表")
        if plotly_available:
          fig = go.Figure()
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["Close"],
                  mode="lines",
                  name="收盤價",
                  line=dict(color="#1f77b4", width=3),
              )
          )
          # 買點標記
          fig.add_trace(
              go.Scatter(
                  x=buy_signals.index,
                  y=buy_signals["Close"],
                  mode="markers",
                  name="建議買進 (Buy)",
                  marker=dict(color="green", size=12, symbol="triangle-up"),
              )
          )
          # 賣點標記
          fig.add_trace(
              go.Scatter(
                  x=sell_signals.index,
                  y=sell_signals["Close"],
                  mode="markers",
                  name="建議賣出 (Sell)",
                  marker=dict(color="red", size=12, symbol="triangle-down"),
              )
          )
          fig.update_layout(
              title=f"{stock_symbol} 買賣訊號點位",
              xaxis_title="日期",
              yaxis_title="價格",
              height=500,
              template="plotly_white",
          )
          st.plotly_chart(fig, use_container_width=True)

      # 標籤 2: 技術分析
      with tab2:
        st.subheader("📈 明顯化均線與 RSI 指標")
        if plotly_available:
          fig = go.Figure()
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["Close"],
                  mode="lines",
                  name="收盤價",
                  line=dict(color="black", width=3),
              )
          )
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA20"],
                  mode="lines",
                  name="20日均線",
                  line=dict(color="orange", width=2.5),
              )
          )
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA50"],
                  mode="lines",
                  name="50日均線",
                  line=dict(color="crimson", width=2.5),
              )
          )
          fig.update_layout(
              title="移動平均線 (線條加粗)",
              xaxis_title="日期",
              yaxis_title="價格",
              height=450,
              template="plotly_white",
          )
          st.plotly_chart(fig, use_container_width=True)

          # RSI 圖表
          fig_rsi = go.Figure()
          fig_rsi.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["RSI"],
                  mode="lines",
                  name="RSI",
                  line=dict(color="purple", width=2.5),
              )
          )
          fig_rsi.add_hline(
              y=70, line_dash="dash", line_color="red", annotation_text="超買 (70)"
          )
          fig_rsi.add_hline(
              y=30,
              line_dash="dash",
              line_color="green",
              annotation_text="超賣 (30)",
          )
          fig_rsi.update_layout(
              title="相對強弱指標 (RSI)", height=350, template="plotly_white"
          )
          st.plotly_chart(fig_rsi, use_container_width=True)

      # 標籤 3: AI 預測
      with tab3:
        st.subheader("🔮 未來 30 天走勢預測")
        data = stock_data[["Close"]].dropna()
        scaler = MinMaxScaler()
        data_scaled = scaler.fit_transform(data[["Close"]])
        X = data_scaled[:-1].reshape(-1, 1)
        y = data["Close"].values[1:]

        model = LinearRegression()
        model.fit(X, y)

        future_days = 30
        last_price = current_price
        predictions = []
        for _ in range(future_days):
          scaled_price = scaler.transform([[last_price]])
          next_price = model.predict(scaled_price)[0]
          predictions.append(next_price)
          last_price = next_price

        future_dates = pd.date_range(
            start=stock_data.index[-1] + timedelta(days=1), periods=future_days
        )
        if plotly_available:
          fig = go.Figure()
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index[-60:],
                  y=stock_data["Close"].iloc[-60:],
                  name="歷史價格",
                  line=dict(color="blue", width=2.5),
              )
          )
          fig.add_trace(
              go.Scatter(
                  x=future_dates,
                  y=predictions,
                  name="預測價格",
                  line=dict(color="red", width=2.5, dash="dash"),
              )
          )
          fig.update_layout(
              title="AI 價格預測曲線", height=450, template="plotly_white"
          )
          st.plotly_chart(fig, use_container_width=True)

      # 標籤 4: 新聞與輿情
      with tab4:
        st.subheader("📰 最新市場與相關新聞頭條")
        try:
          news_list = ticker.news
          if news_list:
            for item in news_list[:5]:
              title = item.get("title", "無標題")
              publisher = item.get("publisher", "Yahoo Finance")
              link = item.get("link", "#")
              st.markdown(f"- **[{title}]({link})** — *{publisher}*")
          else:
            st.info("目前無即時新聞可供顯示。")
        except Exception as e:
          st.warning("無法順لي載入新聞資訊。")

  except Exception as e:
    st.error(f"❌ 錯誤: {str(e)}")
else:
    st.info("👈 請於側邊欄輸入股票代碼")

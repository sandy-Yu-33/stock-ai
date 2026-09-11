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
    page_title="台股智慧 AI 分析與當沖系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 台股智慧 AI 分析與當沖、隔日沖策略系統")
st.markdown("---")

# 側邊欄配置
with st.sidebar:
  st.header("⚙️ 參數設定與市場選股")

  # 股票代碼輸入支援台股與美股
  stock_symbol = st.text_input(
      "輸入股票代碼 (例: 2330, 2344, 2603)",
      value="2330",
      placeholder="輸入代碼",
  )

  # 自動補上 .TW (針對台股上市)
  if stock_symbol.isdigit() and len(stock_symbol) == 4:
    stock_symbol = stock_symbol + ".TW"
  elif stock_symbol.isdigit() and len(stock_symbol) == 5:
    stock_symbol = stock_symbol + ".TWO"  # 櫃買中心

  time_range = st.selectbox(
      "選擇歷史數據範圍", ["1個月", "3個月", "6個月", "1年"]
  )
  period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y"}
  period = period_map[time_range]

  st.markdown("---")
  st.subheader("🌐 國際股市參考")
  for name, sym in {
      "標普500": "^GSPC",
      "那斯達克": "^IXIC",
      "費城半導體": "^SOX",
  }.items():
    try:
      g_df = yf.download(sym, period="3d", progress=False)
      if isinstance(g_df.columns, pd.MultiIndex):
        g_df.columns = g_df.columns.droplevel(1)
      p_curr = float(g_df["Close"].iloc[-1])
      p_prev = float(g_df["Close"].iloc[-2])
      p_chg = ((p_curr - p_prev) / p_prev) * 100
      st.metric(name, f"{p_curr:.2f}", f"{p_chg:+.2f}%")
    except:
      st.text(f"{name}: 載入中...")

# 主程式邏輯
if stock_symbol:
  try:
    with st.spinner(f"正在加載 {stock_symbol} 數據與進行技術運算..."):
      stock_data = yf.download(stock_symbol, period=period, progress=False)

    if stock_data.empty:
      st.error(
          f"❌ 找不到股票代碼: {stock_symbol}。請確認代碼是否正確（例如上市加 .TW，上櫃加 .TWO）。"
      )
    else:
      if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.droplevel(1)

      current_price = float(stock_data["Close"].iloc[-1])
      prev_close = float(stock_data["Close"].iloc[-2])
      chg = current_price - prev_close
      chg_pct = (chg / prev_close) * 100

      # 頂部即時指標
      col1, col2, col3, col4 = st.columns(4)
      col1.metric("當前收盤價", f"${current_price:.2f}", f"{chg:+.2f} ({chg_pct:+.2f}%)")
      col2.metric("區間最高價", f"${float(stock_data['High'].max()):.2f}")
      col3.metric("區間最低價", f"${float(stock_data['Low'].min()):.2f}")
      col4.metric(
          "平均成交量", f"{int(stock_data['Volume'].mean()/1000):,} 張"
      )

      st.markdown("---")

      # 技術指標計算
      stock_data["MA5"] = stock_data["Close"].rolling(5).mean()
      stock_data["MA20"] = stock_data["Close"].rolling(20).mean()
      stock_data["MA60"] = stock_data["Close"].rolling(60).mean()

      # ATR (真實波動幅度範圍) 用於計算目標價
      high_low = stock_data["High"] - stock_data["Low"]
      high_close = np.abs(stock_data["High"] - stock_data["Close"].shift())
      low_close = np.abs(stock_data["Low"] - stock_data["Close"].shift())
      tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
      atr = float(tr.rolling(14).mean().iloc[-1])

      # 目標價計算
      short_target = current_price + atr * 1.5
      short_stoploss = current_price - atr * 1.0
      long_target = current_price * 1.15  # 長期目標 +15%

      # 分頁介面
      tab1, tab2, tab3, tab4 = st.tabs(
          ["🎯 當沖與進出場訊號", "📈 加粗技術線圖", "🔮 AI 目標價預測", "📰 全球財經新聞"]
      )

      # 標籤 1: 策略與訊號
      with tab1:
        st.subheader("⚡ 當沖與隔日沖策略評估")

        col_a, col_b = st.columns(2)
        with col_a:
          st.markdown("#### 🚀 隔日沖選股評分")
          tail_pullup = (stock_data["Close"].iloc[-1] - stock_data["Low"].iloc[-1]) / (
              stock_data["High"].iloc[-1] - stock_data["Low"].iloc[-1] + 1e-6
          )
          vol_surge = (
              stock_data["Volume"].iloc[-1]
              / stock_data["Volume"].rolling(5).mean().iloc[-1]
          )

          if tail_pullup > 0.7 and vol_surge > 1.3:
            st.success(
                "🔥 **符合隔日沖條件**：尾盤急拉收高且成交量放大，適合短多操作。"
            )
          else:
            st.warning("⚠️ **不建議隔日沖**：今日尾盤追價動能不足或量能平緩。")

          st.write(f"- 尾盤收拉強度: `{tail_pullup:.2f}` (大於0.7為佳)")
          st.write(f"- 量能放大倍數: `{vol_surge:.2f}x` (大於1.3倍為佳)")

        with col_b:
          st.markdown("#### ⏱️ 當沖進場訊號")
          ma5_val = float(stock_data["MA5"].iloc[-1])
          if current_price > ma5_val and vol_surge > 1.2:
            st.success(
                "🟢 **強勢多方當沖訊號**：價在 5 日線之上且帶量，逢回找支撐做多。"
            )
          elif current_price < ma5_val:
            st.error(
                "🔴 **弱勢空方當沖訊號**：價跌破 5 日線，盤中反彈可偏空看待。"
            )
          else:
            st.info("⚪ **盤整觀望**：無明顯當沖突破契機。")

          st.write(f"- 短期 5 日支撐價: `{ma5_val:.2f}`")

        st.markdown("---")
        st.markdown("#### 🎯 建議進出場價位規劃")
        p_col1, p_col2, p_col3, p_col4 = st.columns(4)
        p_col1.metric("建議進場點 (Buy)", f"${current_price:.2f}")
        p_col2.metric("短期停損點", f"${short_stoploss:.2f}")
        p_col3.metric("短期目標價 (波段)", f"${short_target:.2f}")
        p_col4.metric("長期目標價 (+15%)", f"${long_target:.2f}")

      # 標籤 2: 技術分析線圖 (加粗版)
      with tab2:
        st.subheader("📈 清晰加粗均線圖表 (MA5, MA20, MA60)")
        if plotly_available:
          fig = go.Figure()
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["Close"],
                  mode="lines",
                  name="收盤價",
                  line=dict(color="#1f77b4", width=3.5),
              )
          )
          fig.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA5"],
                  mode="lines",
                  name="5日均線",
                  line=dict(color="green", width=2.5),
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
                  y=stock_data["MA60"],
                  mode="lines",
                  name="60日季線",
                  line=dict(color="red", width=2.5),
              )
          )
          fig.update_layout(
              title=f"{stock_symbol} 多週期均線走勢",
              xaxis_title="日期",
              yaxis_title="價格",
              height=500,
              template="plotly_white",
          )
          st.plotly_chart(fig, use_container_width=True)

      # 標籤 3: AI 預測
      with tab3:
        st.subheader("🔮 AI 模型短期走勢推演")
        df_model = stock_data[["Close"]].dropna()
        scaler = MinMaxScaler()
        scaled_data = scaler.fit_transform(df_model[["Close"]])
        X = scaled_data[:-1].reshape(-1, 1)
        y = df_model["Close"].values[1:]

        model = LinearRegression()
        model.fit(X, y)

        future_days = 15
        last_val = current_price
        preds = []
        for _ in range(future_days):
          s_val = scaler.transform([[last_val]])
          nxt = model.predict(s_val)[0]
          preds.append(nxt)
          last_val = nxt

        f_dates = pd.date_range(
            start=stock_data.index[-1] + timedelta(days=1), periods=future_days
        )
        if plotly_available:
          fig_p = go.Figure()
          fig_p.add_trace(
              go.Scatter(
                  x=stock_data.index[-40:],
                  y=stock_data["Close"].iloc[-40:],
                  name="近期真實走勢",
                  line=dict(color="blue", width=3),
              )
          )
          fig_p.add_trace(
              go.Scatter(
                  x=f_dates,
                  y=preds,
                  name="AI 預測走勢 (15天)",
                  line=dict(color="magenta", width=3, dash="dash"),
              )
          )
          fig_p.update_layout(
              title="未來 15 個交易日預測曲線", height=450, template="plotly_white"
          )
          st.plotly_chart(fig_p, use_container_width=True)

      # 標籤 4: 國際新聞與網站
      with tab4:
        st.subheader("📰 全球財經與個股即時新聞")
        try:
          news_items = ticker.news
          if news_items:
            for item in news_items[:8]:
              title = item.get("title", "無標題")
              publisher = item.get("publisher", "財經媒體")
              link = item.get("link", "#")
              st.markdown(f"- **[{title}]({link})** — *來源: {publisher}*")
          else:
            st.info(
                "目前無直接新聞推播，建議參考以下全球重要財經資訊網站："
            )
        except:
          st.info("無法直接取得新聞串流。")

        st.markdown("---")
        st.markdown("#### 🌍 推薦全球與台灣主力財經資訊網站")
        st.markdown(
            "- [鉅亨網 (Anue)](https://www.cnyes.com/) - 台灣最即時國際財經與台股新聞"
        )
        st.markdown(
            "- [Yahoo 股市](https://tw.stock.yahoo.com/) - 籌碼、三大法人買賣超與即時報價"
        )
        st.markdown(
            "- [Investing.com](https://www.investing.com/) - 全球期貨、美股、外匯即時走勢"
        )
        st.markdown(
            "- [Bloomberg](https://www.bloomberg.com/) - 國際總經與科技產業動態"
        )

  except Exception as e:
    st.error(f"❌ 系統錯誤: {str(e)}")
else:
  st.info("👈 請於左側邊欄輸入股票代碼以啟動分析系統。")

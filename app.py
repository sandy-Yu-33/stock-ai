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
    page_title="專業台股 AI 智慧分析系統",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📈 專業台股 AI 智慧分析與多功能看盤系統")
st.markdown("---")

# 擴充台股熱門公司對照字典
TW_STOCK_NAMES = {
    "2330": "台積電 (TSMC)",
    "2303": "聯電 (UMC)",
    "2317": "鴻海 (Foxconn)",
    "2454": "聯發科 (MediaTek)",
    "2603": "長榮 (Evergreen)",
    "2609": "陽明 (Yang Ming)",
    "2308": "台達電 (Delta)",
    "2881": "富邦金 (Fubon)",
    "2882": "國泰金 (Cathay)",
    "2891": "中信金 (CTBC)",
    "2002": "中鋼 (China Steel)",
    "1301": "台塑 (Formosa)",
    "2408": "南亞科 (Nanya Tech)",
    "2379": "瑞昱 (Realtek)",
    "3037": "欣興 (Unimicron)",
    "2615": "萬海 (Wan Hai)",
}

# 側邊欄配置
with st.sidebar:
  st.header("⚙️ 搜尋與市場設定")

  user_input = st.text_input(
      "輸入股票代碼或名稱 (例: 2330, 2303, AAPL)",
      value="2330",
      placeholder="輸入代碼",
  )

  # 智慧代碼解析邏輯：支援直接打代號或帶有 .TW/.TWO 的格式
  raw_input = user_input.strip().upper()
  if "." in raw_input:
    stock_symbol = raw_input
    clean_code = raw_input.split(".")[0]
  else:
    clean_code = "".join(filter(str.isdigit, raw_input))
    if len(clean_code) == 4:
      stock_symbol = clean_code + ".TW"
    elif len(clean_code) == 5:
      stock_symbol = clean_code + ".TWO"
    else:
      stock_symbol = raw_input  # 支援美股如 AAPL, TSLA

  company_name = TW_STOCK_NAMES.get(clean_code, f"標的 {stock_symbol}")

  time_range = st.selectbox(
      "選擇歷史走勢區間", ["1個月", "3個月", "6個月", "1年"]
  )
  period_map = {"1個月": "1mo", "3個月": "3mo", "6個月": "6mo", "1年": "1y"}
  period = period_map[time_range]

  st.markdown("---")
  st.subheader("🌐 全球主要期貨與美股")
  for idx_name, sym in {
      "台指期參考": "^TWII",
      "標普 500": "^GSPC",
      "那斯達克": "^IXIC",
      "費城半導體": "^SOX",
  }.items():
    try:
      df_g = yf.download(sym, period="3d", progress=False)
      if isinstance(df_g.columns, pd.MultiIndex):
        df_g.columns = df_g.columns.droplevel(1)
      p_c = float(df_g["Close"].iloc[-1])
      p_p = float(df_g["Close"].iloc[-2])
      p_chg = ((p_c - p_p) / p_p) * 100
      st.metric(idx_name, f"{p_c:,.2f}", f"{p_chg:+.2f}%")
    except:
      st.text(f"{idx_name}: 連線中...")

# 主程式邏輯
if stock_symbol:
  try:
    with st.spinner(f"正在載入 {company_name} ({stock_symbol}) 資料..."):
      # 確保下載格式穩定
      stock_data = yf.download(
          stock_symbol, period=period, interval="1d", progress=False
      )

      # 處理 yfinance 新版 MultiIndex 欄位問題
      if isinstance(stock_data.columns, pd.MultiIndex):
        stock_data.columns = stock_data.columns.droplevel(1)

    if stock_data is None or stock_data.empty or len(stock_data) < 2:
      st.error(
          f"❌ 找不到代碼 `{stock_symbol}` 的資料！請檢查代碼是否正確（台股上市請輸入 4 碼，如 2303；美股請輸入英文代號）。"
      )
    else:
      # 確保數值型態正確
      for col in ["Close", "High", "Low", "Open", "Volume"]:
        if col in stock_data.columns:
          stock_data[col] = pd.to_numeric(stock_data[col], errors="coerce")
      stock_data = stock_data.dropna(subset=["Close"])

      current_price = float(stock_data["Close"].iloc[-1])
      prev_close = float(stock_data["Close"].iloc[-2])
      chg = current_price - prev_close
      chg_pct = (chg / prev_close) * 100

      st.subheader(f"📌 目前檢視標的：{company_name} (`{stock_symbol}`)")

      # 報價面板
      c1, c2, c3, c4 = st.columns(4)
      c1.metric("當前成交價", f"${current_price:.2f}", f"{chg:+.2f} ({chg_pct:+.2f}%)")
      c2.metric("今日最高", f"${float(stock_data['High'].iloc[-1]):.2f}")
      c3.metric("今日最低", f"${float(stock_data['Low'].iloc[-1]):.2f}")
      c4.metric(
          "成交張數", f"{int(stock_data['Volume'].iloc[-1]/1000):,} 張"
      )

      st.markdown("---")

      # 計算技術指標
      stock_data["MA5"] = stock_data["Close"].rolling(5).mean()
      stock_data["MA20"] = stock_data["Close"].rolling(20).mean()
      stock_data["MA60"] = stock_data["Close"].rolling(60).mean()

      delta = stock_data["Close"].diff()
      gain = delta.where(delta > 0, 0).rolling(window=14).mean()
      loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
      rs = gain / loss
      stock_data["RSI"] = 100 - (100 / (1 + rs))

      # 計算 ATR 與目標價
      tr = pd.concat(
          [
              stock_data["High"] - stock_data["Low"],
              np.abs(stock_data["High"] - stock_data["Close"].shift()),
              np.abs(stock_data["Low"] - stock_data["Close"].shift()),
          ],
          axis=1,
      ).max(axis=1)
      atr = float(tr.rolling(14).mean().iloc[-1])

      short_target = current_price + atr * 1.5
      stop_loss = current_price - atr * 1.0
      long_target = current_price * 1.12

      # 產生買賣訊號點
      stock_data["Action"] = "Hold"
      stock_data.loc[
          (stock_data["MA5"] > stock_data["MA20"])
          & (stock_data["RSI"] < 45),
          "Action",
      ] = "Buy"
      stock_data.loc[
          (stock_data["MA5"] < stock_data["MA20"])
          & (stock_data["RSI"] > 60),
          "Action",
      ] = "Sell"

      df_buy = stock_data[stock_data["Action"] == "Buy"]
      df_sell = stock_data[stock_data["Action"] == "Sell"]

      # 分頁切換
      tab1, tab2, tab3, tab4 = st.tabs(
          ["📊 三竹風買賣訊號", "📈 加粗均線與指標", "🎯 當沖/目標價規劃", "📰 相關財經資訊"]
      )

      with tab1:
        st.subheader("🎯 買點 (綠三角) 與 賣點 (紅倒三角) 標示圖")
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
          if not df_buy.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_buy.index,
                    y=df_buy["Close"],
                    mode="markers",
                    name="建議買進 (Buy)",
                    marker=dict(color="green", size=14, symbol="triangle-up"),
                )
            )
          if not df_sell.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_sell.index,
                    y=df_sell["Close"],
                    mode="markers",
                    name="建議賣出 (Sell)",
                    marker=dict(color="red", size=14, symbol="triangle-down"),
                )
            )
          fig.update_layout(
              title=f"{company_name} 歷史買賣點決策",
              xaxis_title="日期",
              yaxis_title="價格",
              height=500,
              template="plotly_white",
          )
          st.plotly_chart(fig, use_container_width=True)

      with tab2:
        st.subheader("📈 清晰多週期均線 (MA5, MA20, MA60)")
        if plotly_available:
          fig2 = go.Figure()
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["Close"],
                  mode="lines",
                  name="收盤價",
                  line=dict(color="black", width=3),
              )
          )
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA5"],
                  mode="lines",
                  name="5日線",
                  line=dict(color="green", width=2.5),
              )
          )
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA20"],
                  mode="lines",
                  name="20日線",
                  line=dict(color="orange", width=2.5),
              )
          )
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA60"],
                  mode="lines",
                  name="60日季線",
                  line=dict(color="red", width=2.5),
              )
          )
          fig2.update_layout(
              title="移動平均線走勢", height=450, template="plotly_white"
          )
          st.plotly_chart(fig2, use_container_width=True)

      with tab3:
        st.subheader("⚡ 實戰交易策略與目標價規劃")
        col_s1, col_s2 = st.columns(2)
        with col_s1:
          st.markdown("#### 🚀 隔日沖與當沖評估")
          tail_p = (stock_data["Close"].iloc[-1] - stock_data["Low"].iloc[-1]) / (
              stock_data["High"].iloc[-1] - stock_data["Low"].iloc[-1] + 1e-6
          )
          vol_s = (
              stock_data["Volume"].iloc[-1]
              / stock_data["Volume"].rolling(5).mean().iloc[-1]
          )
          if tail_p > 0.65 and vol_s > 1.2:
            st.success("🔥 **強烈推薦隔日沖**：尾盤帶量上拉，具備開高優勢。")
          else:
            st.info("⚪ **一般盤勢**：量價結構平穩，依技術支撐操作。")
          st.write(f"- 尾盤收拉強度: `{tail_p:.2f}`")
          st.write(f"- 成交量放大倍數: `{vol_s:.2f}x`")

        with col_s2:
          st.markdown("#### 🎯 目標價與停損點設定")
          st.metric("建議進場參考價", f"${current_price:.2f}")
          st.metric("短期波段目標價", f"${short_target:.2f}")
          st.metric("長期核心目標價", f"${long_target:.2f}")
          st.metric("建議停損價", f"${stop_loss:.2f}")

      with tab4:
        st.subheader("📰 專業財經資訊與看盤網站")
        st.markdown(
            "- [鉅亨網台股頻道](https://www.cnyes.com/twstock) - 深入產業分析"
        )
        st.markdown(
            "- [Yahoo 股市](https://tw.stock.yahoo.com/) - 三大法人籌碼與即時報價"
        )
        st.markdown(
            "- [Investing.com 台灣](https://tw.investing.com/) - 國際期貨與外匯"
        )

  except Exception as e:
    st.error(f"❌ 系統錯誤: {str(e)}")
else:
  st.info("👈 請於左側邊欄輸入股票代碼開始分析。")

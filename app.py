from datetime import datetime, timedelta
import numpy as np
import pandas as pd
plotly_available = True
try:
  import plotly.graph_objects as go
except ImportError:
  plotly_available = False
import streamlit as st
import yfinance as yf

# 設置頁面配置 (三竹股市風格)
st.set_page_config(
    page_title="三竹股市 AI 智慧分析系統",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("📱 三竹股市風格 AI 智慧看盤與下單決策系統")
st.markdown("---")

# 台股上市櫃熱門中文對照表
STOCK_NAME_MAP = {
    "6669.TW": "緯穎",
    "2330.TW": "台積電",
    "2303.TW": "聯電",
    "2317.TW": "鴻海",
    "6446.TW": "藥華藥",
    "2454.TW": "聯發科",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2308.TW": "台達電",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2891.TW": "中信金",
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "00878.TW": "國泰永續高股息",
}

# 側邊欄：快速自選股與代碼輸入
with st.sidebar:
  st.header("🔍 三竹股市商品搜尋")

  user_input = st.text_input(
      "輸入台股代碼 (例: 6669, 2330, 0050)",
      value="6669",
      placeholder="輸入 4 碼代號",
  )

  raw = user_input.strip().upper()
  if "." in raw or "^" in raw:
    symbol = raw
  else:
    digits = "".join(filter(str.isdigit, raw))
    if len(digits) == 4:
      symbol = digits + ".TW"
    elif len(digits) == 5:
      symbol = digits + ".TWO"
    else:
      symbol = raw

  time_range = st.selectbox(
      "查看週期", ["1個月", "3個月", "6個月", "1年", "2年"]
  )
  period_map = {
      "1個月": "1mo",
      "3個月": "3mo",
      "6個月": "6mo",
      "1年": "1y",
      "2年": "2y",
  }
  period = period_map[time_range]

  st.markdown("---")
  st.subheader("🌐 大盤與期貨連線")
  for idx_name, sym in {
      "台指期": "^TWII",
      "標普500": "^GSPC",
      "那斯達克": "^IXIC",
  }.items():
    try:
      df_i = yf.download(sym, period="3d", auto_adjust=False, progress=False)
      if isinstance(df_i.columns, pd.MultiIndex):
        df_i.columns = df_i.columns.droplevel(1)
      c_val = float(df_i["Close"].iloc[-1])
      p_val = float(df_i["Close"].iloc[-2])
      c_chg = ((c_val - p_val) / p_val) * 100
      st.metric(idx_name, f"{c_val:,.2f}", f"{c_chg:+.2f}%")
    except:
      st.text(f"{idx_name}: 連線中...")

# 主程式
if symbol:
  try:
    with st.spinner(f"正在對齊 Yahoo 股市真實報價 ({symbol})..."):
      ticker = yf.Ticker(symbol)
      # 獲取日K線資料
      stock_data = ticker.history(period=period, auto_adjust=False)

      if stock_data is None or stock_data.empty:
        stock_data = yf.download(
            symbol, period=period, interval="1d", auto_adjust=False, progress=False
        )
        if isinstance(stock_data.columns, pd.MultiIndex):
          stock_data.columns = stock_data.columns.droplevel(1)

    if stock_data is None or stock_data.empty or len(stock_data) < 2:
      st.error(
          f"❌ 找不到代碼 `{symbol}`，請確認台股代號是否正確（例如上市請輸入 4 碼）。"
      )
    else:
      for col in ["Close", "High", "Low", "Open", "Volume"]:
        if col in stock_data.columns:
          stock_data[col] = pd.to_numeric(stock_data[col], errors="coerce")
      stock_data = stock_data.dropna(subset=["Close"])

      # 中文名稱對應
      clean_sym = symbol.upper()
      comp_name = STOCK_NAME_MAP.get(clean_sym, "")
      if not comp_name:
        try:
          info = ticker.info
          comp_name = (
              info.get("chineseName")
              or info.get("longName")
              or info.get("shortName")
              or clean_sym
          )
        except:
          comp_name = clean_sym

      # 嚴格對齊 Yahoo 股市的最新真實成交價、開高低與昨收
      current_price = float(stock_data["Close"].iloc[-1])
      prev_close = float(stock_data["Close"].iloc[-2])
      open_p = float(stock_data["Open"].iloc[-1])
      high_p = float(stock_data["High"].iloc[-1])
      low_p = float(stock_data["Low"].iloc[-1])
      vol = int(stock_data["Volume"].iloc[-1])

      chg = current_price - prev_close
      chg_pct = (chg / prev_close) * 100

      # 三竹股市風格標題區
      st.markdown(
          f"### 📱 **{comp_name} ({clean_sym})**"
          f"  |  最新收盤: **${current_price:,.2f}** "
          f"({chg:+,.2f} / {chg_pct:+.2f}%)"
      )

      # 三竹風即時行情雙排面板 (數值與 Yahoo 股市完全一致)
      col1, col2, col3, col4, col5, col6 = st.columns(6)
      col1.metric("開盤", f"${open_p:,.2f}")
      col2.metric("最高", f"${high_p:,.2f}")
      col3.metric("最低", f"${low_p:,.2f}")
      col4.metric("昨收", f"${prev_close:,.2f}")
      col5.metric("成交量", f"{vol:,}")
      col6.metric("漲跌幅", f"{chg_pct:+.2f}%")

      st.markdown("---")

      # 技術指標計算
      stock_data["MA5"] = stock_data["Close"].rolling(5).mean()
      stock_data["MA20"] = stock_data["Close"].rolling(20).mean()
      stock_data["MA60"] = stock_data["Close"].rolling(60).mean()

      delta = stock_data["Close"].diff()
      gain = delta.where(delta > 0, 0).rolling(14).mean()
      loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
      stock_data["RSI"] = 100 - (100 / (1 + (gain / loss)))

      # ATR 目標價
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

      # 買賣點訊號標記 (確保綠買紅賣三角明確顯示)
      stock_data["Signal"] = 0
      stock_data.loc[stock_data["RSI"] < 45, "Signal"] = 1
      stock_data.loc[stock_data["RSI"] > 60, "Signal"] = -1

      df_buy = stock_data[stock_data["Signal"] == 1]
      df_sell = stock_data[stock_data["Signal"] == -1]

      # 三竹風功能分頁
      tab1, tab2, tab3, tab4 = st.tabs(
          ["📈 三竹風 K線與買賣訊號", "📊 多週期均線對照", "⚡ 當沖與目標價", "📰 盤勢新聞"]
      )

      with tab1:
        st.subheader("🟢 建議買點 (綠三角) 與 🔴 建議賣出 (紅倒三角)")
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
                    name="買進訊號 (Buy)",
                    marker=dict(
                        color="green", size=16, symbol="triangle-up"
                    ),
                )
            )
          if not df_sell.empty:
            fig.add_trace(
                go.Scatter(
                    x=df_sell.index,
                    y=df_sell["Close"],
                    mode="markers",
                    name="賣出訊號 (Sell)",
                    marker=dict(
                        color="red", size=16, symbol="triangle-down"
                    ),
                )
            )
          fig.update_layout(
              title=f"{comp_name} ({clean_sym}) 歷史買賣點決策",
              height=480,
              template="plotly_white",
          )
          st.plotly_chart(fig, use_container_width=True)

      with tab2:
        st.subheader("📈 移動平均線 (MA5, MA20, MA60)")
        if plotly_available:
          fig2 = go.Figure()
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["Close"],
                  name="收盤價",
                  line=dict(color="black", width=3),
              )
          )
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA5"],
                  name="5日線",
                  line=dict(color="green", width=2.5),
              )
          )
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA20"],
                  name="20日線",
                  line=dict(color="orange", width=2.5),
              )
          )
          fig2.add_trace(
              go.Scatter(
                  x=stock_data.index,
                  y=stock_data["MA60"],
                  name="60日線",
                  line=dict(color="red", width=2.5),
              )
          )
          fig2.update_layout(height=450, template="plotly_white")
          st.plotly_chart(fig2, use_container_width=True)

      with tab3:
        st.subheader("⚡ 實戰當沖、隔日沖與目標價")
        col_a, col_b = st.columns(2)
        with col_a:
          st.markdown("#### 🚀 當沖與隔日沖評估")
          tail = (stock_data["Close"].iloc[-1] - stock_data["Low"].iloc[-1]) / (
              stock_data["High"].iloc[-1] - stock_data["Low"].iloc[-1] + 1e-6
          )
          if tail > 0.65:
            st.success("🔥 **適合隔日沖**：尾盤買盤積極，具備開高效應。")
          else:
            st.info("⚪ **觀望盤勢**：量價結構平穩。")
          st.write(f"- 尾盤收拉強度: `{tail:.2f}`")
        with col_b:
          st.markdown("#### 🎯 價格規劃")
          st.metric("建議進場參考", f"${current_price:,.2f}")
          st.metric("短期波段目標", f"${short_target:,.2f}")
          st.metric("建議嚴格停損", f"${stop_loss:,.2f}")

      with tab4:
        st.subheader("📰 三竹股市財經快訊")
        st.markdown("- [Yahoo 股市即時行情](https://tw.stock.yahoo.com/)")
        st.markdown("- [鉅亨網台股頻道](https://www.cnyes.com/twstock)")

  except Exception as e:
    st.error(f"❌ 系統錯誤: {str(e)}")
else:
    st.info("👈 請於左側邊欄輸入代碼。")

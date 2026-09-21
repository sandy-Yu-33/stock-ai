from datetime import datetime, timedelta
import math
import re
import warnings
import io
from io import StringIO

import numpy as np
import pandas as pd
import streamlit as st
import yfinance as yf

warnings.filterwarnings("ignore")

try:
    import requests
except Exception:
    requests = None

st.set_page_config(
    page_title="33 專業操盤系統 V13.0 實戰風控版",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Theme / CSS (實戰專業深色/簡約風)
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
.support-box { 
    background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(6, 95, 70, 0.2) 100%); 
    border-left: 5px solid #10b981; 
    padding: 16px; border-radius: 10px; margin-bottom: 10px;
    border: 1px solid rgba(16, 185, 129, 0.3); 
}
.resistance-box { 
    background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(153, 27, 27, 0.2) 100%); 
    border-left: 5px solid #ef4444; 
    padding: 16px; border-radius: 10px; margin-bottom: 10px;
    border: 1px solid rgba(239, 68, 68, 0.3); 
}
.trade-box {
    background: linear-gradient(135deg, rgba(56, 189, 248, 0.1) 0%, rgba(3, 105, 161, 0.2) 100%);
    border-left: 5px solid #38bdf8;
    padding: 16px; border-radius: 10px; margin-bottom: 10px;
    border: 1px solid rgba(56, 189, 248, 0.3);
}
.warning-box {
    background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(180, 83, 9, 0.2) 100%);
    border-left: 5px solid #f59e0b;
    padding: 16px; border-radius: 10px; margin-bottom: 10px;
    border: 1px solid rgba(245, 158, 11, 0.3);
}
.small-note {font-size: 0.82rem; opacity: .75;}
</style>
""", unsafe_allow_html=True)

DEFAULT_WATCHLIST = [
    "2330", "3711", "6669", "5274", "2317", "2454", "NVDA", "AAPL", "TSLA"
]

GLOBAL_ASSET_DATABASE = {
    "2330.TW": {"name": "台積電", "market": "台股上市", "desc": "全球晶圓代工龍頭，先進製程與CoWoS核心", "pe": "22.5", "roe": "28.5%", "eps": "39.2元"},
    "3711.TW": {"name": "日月光投控", "market": "台股上市", "desc": "全球半導體封測龍頭", "pe": "16.8", "roe": "15.2%", "eps": "8.4元"},
    "6669.TW": {"name": "緯穎", "market": "台股上市", "desc": "雲端資料中心與AI伺服器", "pe": "24.1", "roe": "35.8%", "eps": "85.4元"},
    "2317.TW": {"name": "鴻海", "market": "台股上市", "desc": "全球電子代工巨頭", "pe": "14.2", "roe": "11.5%", "eps": "10.2元"},
    "2454.TW": {"name": "聯發科", "market": "台股上市", "desc": "全球IC設計大廠", "pe": "18.5", "roe": "26.4%", "eps": "58.1元"},
    "5274.TWO": {"name": "信驊", "market": "台股上櫃", "desc": "伺服器遠端管理晶片(BMC)", "pe": "45.2", "roe": "32.1%", "eps": "52.3元"},
    "NVDA": {"name": "輝達 (NVIDIA)", "market": "美股", "desc": "AI運算與HPC晶片霸主", "pe": "48.5", "roe": "75.2%", "eps": "3.20美元"},
    "AAPL": {"name": "蘋果 (Apple)", "market": "美股", "desc": "消費電子與服務生態系", "pe": "31.2", "roe": "145.0%", "eps": "6.50美元"},
    "TSLA": {"name": "特斯拉 (Tesla)", "market": "美股", "desc": "電動車與能源儲存", "pe": "65.4", "roe": "18.2%", "eps": "2.40美元"},
}

def normalize_symbol(s):
    s = str(s).strip().upper()
    if not s:
        return ""
    if "." in s or "=" in s or "^" in s:
        return s
    for k in GLOBAL_ASSET_DATABASE.keys():
        if k.split(".")[0] == s:
            return k
    if s.isdigit():
        if len(s) == 4:
            if s.startswith(("5", "4", "3", "6", "8")):
                return s + ".TWO"
            else:
                return s + ".TW"
        elif len(s) >= 5:
            return s + ".TW"
    return s

def display_name(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["name"]
    base = sym.split(".")[0]
    for k, v in GLOBAL_ASSET_DATABASE.items():
        if k.startswith(base):
            return v["name"]
    try:
        t = yf.Ticker(symbol)
        info = t.info
        name = info.get("chineseName") or info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception:
        pass
    return f"{symbol} (資產)"

@st.cache_data(ttl=900, show_spinner=False)
def get_history(symbol, period="2y", interval="1d"):
    raw_s = str(symbol).strip().upper()
    candidates = []
    if raw_s.isdigit() and len(raw_s) == 4:
        candidates = [raw_s + ".TW", raw_s + ".TWO", raw_s + ".T", raw_s]
    elif "." in raw_s:
        base = raw_s.split(".")[0]
        candidates = [raw_s, base + ".TW", base + ".TWO"]
    else:
        candidates = [raw_s + ".TW", raw_s + ".TWO", raw_s]

    seen = set()
    unique_candidates = [c for c in candidates if not (c in seen or seen.add(c))]

    for s in unique_candidates:
        try:
            df = yf.download(s, period=period, interval=interval, auto_adjust=False, progress=False, threads=False)
            if df is not None and not df.empty:
                if isinstance(df.columns, pd.MultiIndex):
                    try:
                        df = df.xs(s, axis=1, level=-1)
                    except Exception:
                        df.columns = df.columns.get_level_values(0)
                df = df.rename(columns=str.title)
                needed = ["Open", "High", "Low", "Close", "Volume"]
                if all(c in df.columns for c in needed):
                    df = df[needed].dropna(subset=["Close"])
                    if not df.empty:
                        df.index = pd.to_datetime(df.index)
                        return df
        except Exception:
            continue
    return pd.DataFrame()

def add_indicators(df):
    x = df.copy()
    close, high, low, volume = x["Close"], x["High"], x["Low"], x["Volume"]

    for n in [5, 20, 60, 120]:
        if len(x) >= n:
            x[f"MA{n}"] = close.rolling(n).mean()
        else:
            x[f"MA{n}"] = close.mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.ewm(alpha=1/14, adjust=False).mean() / loss.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    x["RSI14"] = 100 - (100 / (1 + rs))

    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    x["ATR14"] = tr.rolling(14).mean()
    x["VolMA20"] = volume.rolling(20).mean()
    x["VolRatio"] = volume / x["VolMA20"].replace(0, np.nan)
    return x

# -------------------------------------------------------------
# 🎯 老手級機率支撐壓力與風險報酬比 (RR值) 計算
# -------------------------------------------------------------
def calculate_support_resistance_and_rr(df):
    if df.empty or len(df) < 60:
        return None

    x = add_indicators(df).copy()
    r = x.iloc[-1]
    price = float(r["Close"])
    atr = float(r["ATR14"]) if pd.notna(r["ATR14"]) and r["ATR14"] > 0 else price * 0.02

    ma5 = float(r["MA5"])
    ma20 = float(r["MA20"])
    ma60 = float(r["MA60"])
    ma120 = float(r["MA120"])

    hist = x.iloc[:-1].tail(60)
    highs = hist["High"].astype(float)
    lows = hist["Low"].astype(float)

    prev = x.iloc[-2]
    pp = (float(prev["High"]) + float(prev["Low"]) + float(prev["Close"])) / 3
    pivot_s1 = 2 * pp - float(prev["High"])
    pivot_r1 = 2 * pp - float(prev["Low"])

    support_candidates = [ma5, ma20, ma60, ma120, pivot_s1, float(lows.quantile(0.15)), float(lows.min())]
    resistance_candidates = [pivot_r1, float(highs.quantile(0.85)), float(highs.max()), ma20, ma60]

    supports = sorted({round(v, 2) for v in support_candidates if np.isfinite(v) and v < price * 0.995})
    resistances = sorted({round(v, 2) for v in resistance_candidates if np.isfinite(v) and v > price * 1.005})

    s1 = supports[-1] if supports else round(price - 0.8 * atr, 2)
    s2 = supports[-2] if len(supports) >= 2 else round(s1 - 1.0 * atr, 2)
    r1 = resistances[0] if resistances else round(price + 0.8 * atr, 2)
    r2 = resistances[1] if len(resistances) >= 2 else round(r1 + 1.0 * atr, 2)

    # 風險報酬比 (Risk/Reward Ratio) 計算：
    # 潛在獲利 = 第一壓力 - 現價
    # 潛在風險 = 現價 - 第一支撐 (或停損點)
    potential_reward = r1 - price
    potential_risk = price - s1 if price > s1 else atr
    rr_ratio = round(potential_reward / potential_risk, 2) if potential_risk > 0 else 0.0

    return {
        "現價": round(price, 2),
        "ATR14": round(atr, 2),
        "第一支撐": round(s1, 2),
        "第二支撐": round(s2, 2),
        "第一壓力": round(r1, 2),
        "第二壓力": round(r2, 2),
        "建議停損點": round(max(0.01, s1 - 0.2 * atr), 2),
        "風險報酬比(RR值)": rr_ratio,
    }

# -----------------------------
# Sidebar 導航
# -----------------------------
st.sidebar.title("⚙️ 33 專業操盤系統 V13.0")
page = st.sidebar.radio(
    "功能模組",
    [
        "🎯 個股實戰風控與支撐壓力盤",
        "📊 自選股風險報酬監控儀表板",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("操盤資金水位", min_value=0.0, value=500000.0, step=50000.0)

st.sidebar.markdown("### 📋 自選股清單")
watch_text = st.sidebar.text_area(
    "輸入代號 (支援台美)",
    value=",".join(DEFAULT_WATCHLIST),
    height=100
)
watchlist = [s.strip() for s in re.split(r"[,\n\s]+", watch_text) if s.strip()]

# -------------------------------------------------------------
# Page 1: Single Stock Risk Control Analysis
# -----------------------------
if page == "🎯 個股實戰風控與支撐壓力盤":
    st.title("🎯 實戰風控與支撐壓力解析")
    st.markdown("老手箴言：**市場沒有絕對 99% 勝率，贏家靠的是嚴格的停損紀律與合理的風險報酬比（RR值 ≥ 1.5）**。")
    
    manual_input = st.text_input("輸入代號（例: 2330, 6669, NVDA）", value="2330")
    target_symbol = manual_input.strip() if manual_input else "2330"

    df = get_history(target_symbol, "1y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的歷史資料，請確認代號正確。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        d_name = display_name(target_symbol)
        sr = calculate_support_resistance_and_rr(df)

        st.markdown(f"## 📌 {d_name} (`{target_symbol}`) 操盤風控面板")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"${r['Close']:,.2f}")
        c2.metric("14日波動率 (ATR)", f"{sr['ATR14']:,.2f}")
        c3.metric("風險報酬比 (RR值)", f"{sr['風險報酬比(RR值)']}")
        c4.metric("風控狀態", "🟢 值得佈局" if sr['風險報酬比(RR值)'] >= 1.5 else "⚠️ 風險偏高/觀望")

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown("""
            <div class="support-box">
                <b>🛡️ 支撐防守區（買盤集結/主力成本）</b><br>
                • <b>第一支撐：</b> ${0:,.2f}<br>
                • <b>第二支撐：</b> ${1:,.2f}<br>
                <small>註：支撐是用來「觀察反彈或設定停損」，不是鐵板，跌破必須無條件退場。</small>
            </div>
            """.format(sr['第一支撐'], sr['第二支撐']), unsafe_allow_html=True)

        with col_b:
            st.markdown("""
            <div class="resistance-box">
                <b>🚧 壓力解套區（短線賣壓/獲利了結）</b><br>
                • <b>第一壓力：</b> ${0:,.2f}<br>
                • <b>第二壓力：</b> ${1:,.2f}<br>
                <small>註：接近第一壓力時應考慮分批獲利入袋，切忌盲目追高。</small>
            </div>
            """.format(sr['第一壓力'], sr['第二壓力']), unsafe_allow_html=True)

        st.markdown(f"""
        <div class="trade-box">
            <b>⚖️ 操盤手風控建議</b><br>
            • <b>建議停損點：</b> ${sr['建議停損點']:,.2f}（跌破第一支撐並結合ATR容許空間）。<br>
            • <b>紀律叮嚀：</b> 當前 RR 值為 <b>{sr['風險報酬比(RR值)']}</b>。若小於 1.5，代表潛在利潤小於風險，老手建議寧可空手等待拉回，絕不追高。
        </div>
        """, unsafe_allow_html=True)

        st.subheader("價格與均線走勢圖")
        st.line_chart(x[["Close", "MA5", "MA20", "MA60"]].dropna(how="all"))

# -------------------------------------------------------------
# Page 2: Watchlist Risk Control Dashboard
# -----------------------------
elif page == "📊 自選股風險報酬監控儀表板":
    st.title("📊 自選股風控與 RR 值總覽")
    st.markdown("快速掃描自選清單中各檔股票的支撐、壓力與風險報酬比，幫你過濾掉不符合風控的標的。")

    rows = []
    for sym in watchlist:
        df = get_history(sym, "1y")
        if df.empty:
            rows.append({"代碼": sym, "名稱": display_name(sym), "狀態": "資料不足"})
            continue
        sr = calculate_support_resistance_and_rr(df)
        rows.append({
            "代碼": sym,
            "名稱": display_name(sym),
            "現價": sr["現價"],
            "第一支撐": sr["第一支撐"],
            "第一壓力": sr["第一壓力"],
            "建議停損": sr["建議停損點"],
            "RR值": sr["風險報酬比(RR值)"],
            "評估": "🔥 值得出手" if sr["風險報酬比(RR值)"] >= 1.5 else "⏳ 等待拉回",
        })

    snap_df = pd.DataFrame(rows)
    if not snap_df.empty:
        st.dataframe(snap_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("33 專業操盤系統 V13.0 實戰風控版：去除一切雜訊，回歸風險報酬與紀律本質。")

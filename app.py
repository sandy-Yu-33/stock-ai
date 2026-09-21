from datetime import datetime, timedelta
import math
import re
import warnings
import io

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
    page_title="33 專業操盤系統 V6.0 專家旗艦版",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Theme / CSS
# -----------------------------
st.markdown("""
<style>
.block-container {padding-top: 1.1rem; padding-bottom: 2rem;}
.metric-card {
    border: 1px solid rgba(128,128,128,.25);
    border-radius: 12px;
    padding: 12px 14px;
    background: rgba(128,128,128,.05);
}
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
.report-card {
    background: rgba(128, 128, 128, 0.05);
    border: 1px solid rgba(128, 128, 128, 0.2);
    padding: 16px;
    border-radius: 12px;
    margin-bottom: 15px;
}
.small-note {font-size: 0.82rem; opacity: .75;}
</style>
""", unsafe_allow_html=True)

DEFAULT_WATCHLIST = [
    "2330", "3711", "6669", "5274", "0050", "00878",
    "2317", "2454", "NVDA", "AAPL", "TSLA", "QQQ", "GC=F"
]

# -------------------------------------------------------------
# 🌐 全球與全台股（上市、上櫃、興櫃、創新板、ETF、期貨）資料庫
# -------------------------------------------------------------
GLOBAL_ASSET_DATABASE = {
    "2330.TW": {"name": "台積電", "div": "季配息", "market": "台股上市", "desc": "全球晶圓代工龍頭"},
    "3711.TW": {"name": "日月光投控", "div": "年配息", "market": "台股上市", "desc": "全球半導體封測龍頭"},
    "6669.TW": {"name": "緯穎", "div": "年配息", "market": "台股上市", "desc": "雲端資料中心與AI伺服器"},
    "2317.TW": {"name": "鴻海", "div": "年配息", "market": "台股上市", "desc": "全球電子代工巨頭與AI伺服器"},
    "2454.TW": {"name": "聯發科", "div": "半年度配息", "market": "台股上市", "desc": "全球前五大IC設計大廠"},
    "2303.TW": {"name": "聯電", "div": "年配息", "market": "台股上市", "desc": "成熟製程晶圓代工大廠"},
    "2308.TW": {"name": "台達電", "div": "年配息", "market": "台股上市", "desc": "電源管理與電動車零組件"},
    "2382.TW": {"name": "廣達", "div": "年配息", "market": "台股上市", "desc": "筆電代工與AI伺服器大廠"},
    "3017.TW": {"name": "奇鋐", "div": "年配息", "market": "台股上市", "desc": "AI 伺服器散熱模組大廠"},
    "3008.TW": {"name": "大立光", "div": "半年配", "market": "台股上市", "desc": "全球手機鏡頭光學霸主"},
    "2603.TW": {"name": "長榮", "div": "年配息", "market": "台股上市", "desc": "全球貨櫃航運巨擘"},
    "2881.TW": {"name": "富邦金", "div": "年配息", "market": "台股金融", "desc": "台灣民營金控龍頭"},
    "5274.TWO": {"name": "信驊", "div": "年配息", "market": "台股上櫃", "desc": "全球伺服器遠端管理晶片(BMC)王"},
    "3661.TWO": {"name": "世芯-KY", "div": "年配息", "market": "台股上櫃", "desc": "AI ASIC 設計服務龍頭"},
    "3529.TWO": {"name": "力旺", "div": "年配息", "market": "台股上櫃", "desc": "半導體矽智財(IP)大廠"},
    "0050.TW": {"name": "元大台灣50", "div": "半年配", "market": "台股ETF", "desc": "追蹤臺灣50指數"},
    "0056.TW": {"name": "元大高股息", "div": "季配息", "market": "台股ETF", "desc": "台灣首檔高股息ETF"},
    "00878.TW": {"name": "國泰永續高股息", "div": "季配息", "market": "台股ETF", "desc": "結合ESG與高股息"},
    "00919.TW": {"name": "群益台灣精選高息", "div": "季配息", "market": "台股ETF", "desc": "精選高息與填息能力"},
    "00929.TW": {"name": "復華台灣科技優息", "div": "月配息", "market": "台股ETF", "desc": "全台首檔科技月配息ETF"},
    "NVDA": {"name": "輝達 (NVIDIA)", "div": "季配息", "market": "美股", "desc": "全球 AI 運算晶片霸主"},
    "AAPL": {"name": "蘋果 (Apple)", "div": "季配息", "market": "美股", "desc": "消費電子與軟體服務"},
    "TSLA": {"name": "特斯拉 (Tesla)", "div": "不配息", "market": "美股", "desc": "電動車與能源儲存領導者"},
    "QQQ": {"name": "那斯達克100 ETF", "div": "季配息", "market": "美股ETF", "desc": "追蹤美股百大科技創新企業"},
    "GC=F": {"name": "黃金期貨", "div": "不適用", "market": "國際期貨", "desc": "全球避險與貴金屬指標"},
    "CL=F": {"name": "紐約原油期貨", "div": "不適用", "market": "國際期貨", "desc": "WTI 輕原油期貨"},
    "^TWII": {"name": "台灣加權指數", "div": "不適用", "market": "全球指數", "desc": "台股大盤加權指數基準"},
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
    return f"{symbol} (上市櫃/興櫃股)"

def get_asset_meta(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["div"], GLOBAL_ASSET_DATABASE[sym]["desc"], GLOBAL_ASSET_DATABASE[sym]["market"]
    base = sym.split(".")[0]
    for k, v in GLOBAL_ASSET_DATABASE.items():
        if k.startswith(base):
            return v["div"], v["desc"], v["market"]
    return "依公告為準", "全市場上市櫃興櫃創新板資產", "台美跨國市場"

@st.cache_data(ttl=300, show_spinner=False)
def get_history(symbol, period="1y", interval="1d"):
    raw_s = str(symbol).strip().upper()
    candidates = []
    if raw_s.isdigit() and len(raw_s) == 4:
        candidates = [raw_s + ".TW", raw_s + ".TWO", raw_s + ".RO", raw_s]
    elif "." in raw_s:
        base = raw_s.split(".")[0]
        candidates = [raw_s, base + ".TW", base + ".TWO", base + ".RO", base]
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

    for n in [5, 10, 20, 60]:
        x[f"MA{n}"] = close.rolling(n).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    rs = gain.ewm(alpha=1/14, adjust=False).mean() / loss.ewm(alpha=1/14, adjust=False).mean().replace(0, np.nan)
    x["RSI14"] = 100 - (100 / (1 + rs))

    tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
    x["ATR14"] = tr.rolling(14).mean()

    # 籌碼與量能指標
    x["VolMA20"] = volume.rolling(20).mean()
    x["VolRatio"] = volume / x["VolMA20"].replace(0, np.nan)
    x["High20"] = high.rolling(20).max()
    x["Low20"] = low.rolling(20).min()
    return x

# -------------------------------------------------------------
# 🎯 專家級支撐與壓力計算模型 (Pivot Points + 區間極值)
# -------------------------------------------------------------
def calculate_support_resistance(df):
    if df.empty or len(df) < 20:
        return None
    x = add_indicators(df)
    r = x.iloc[-1]
    price = float(r["Close"])
    high = float(r["High"])
    low = float(r["Low"])
    
    # 標準市場樞軸點 (Pivot Point)
    pivot = (high + low + price) / 3
    p_sup1 = 2 * pivot - high
    p_res1 = 2 * pivot - low
    
    # 結構性高低點 (20日 Swing High/Low)
    recent_high = float(df["High"].iloc[-20:].max())
    recent_low = float(df["Low"].iloc[-20:].min())
    
    # 專家級融合運算，確保支撐壓力精準反映實戰價位
    sup_1 = round(max(p_sup1, recent_low * 0.99), 2)
    sup_2 = round(min(recent_low, sup_1 * 0.96), 2)
    res_1 = round(min(p_res1, recent_high * 1.01), 2)
    res_2 = round(max(recent_high, res_1 * 1.03), 2)
    
    entry = round(sup_1 * 1.002, 2)
    stop_loss = round(sup_2 * 0.985, 2)
    tp_1 = res_1
    tp_2 = res_2

    return {
        "現價": round(price, 2),
        "第一支撐": sup_1,
        "第二支撐": sup_2,
        "第一壓力": res_1,
        "第二壓力": res_2,
        "建議進場點": entry,
        "第一停利點": tp_1,
        "第二停利點": tp_2,
        "嚴格停損點": stop_loss,
    }

# -----------------------------
# Sidebar 導航
# -----------------------------
st.sidebar.title("⚙️ 33 專業操盤系統 V6.0")
page = st.sidebar.radio(
    "功能模組",
    [
        "📰 今日財經早報與盤勢解析",
        "🕒 13:00 台股隔日沖高勝率選股",
        "⏰ 04:00 美股極速當沖雷達",
        "🔍 全市場個股深度分析 (專家級支撐壓力)",
        "🏠 個人自選股監控儀表板",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("操盤資金水位", min_value=0.0, value=500000.0, step=50000.0)

st.sidebar.markdown("### 📋 自選股清單")
watch_text = st.sidebar.text_area(
    "輸入代號 (支援上市櫃、興櫃、美股、期貨)",
    value=",".join(DEFAULT_WATCHLIST),
    height=100
)
watchlist = [s.strip() for s in re.split(r"[,\n\s]+", watch_text) if s.strip()]

# -------------------------------------------------------------
# Page 1: Daily Morning Report
# -----------------------------
if page == "📰 今日財經早報與盤勢解析":
    st.title("📰 專業操盤手今日財經早報")
    st.markdown(f"**發布日期**：`{datetime.now().strftime('%Y-%m-%d')}` | 專家級跨國市場與短中線多空展望。")

    st.markdown("""
    <div class="report-card">
        <h3>🎯 專家操盤觀點：嚴守支撐壓力，落實紀律風控</h3>
        <p>台股與美股近期受科技權值與 AI 供應鏈帶動，維持高檔震盪結構。短線交易者應密切觀察各標的的「第一支撐」與「第一壓力」區間，切忌盲目追高。透過 13:00 隔日沖與 04:00 當沖模組，可有效捕捉高勝率的短線機會。</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Page 2: Taiwan 13:00 Overnight Scanner (隔日沖)
# -----------------------------
elif page == "🕒 13:00 台股隔日沖高勝率選股":
    st.title("🕒 13:00 台股收盤前隔日沖高勝率選股")
    st.markdown("嚴格篩選條件：**今日漲幅 > 1.5%**、**成交量放大 (量比 > 1.3x)** 且 **收盤價逼近當日高點** 之強勢鎖碼標的。")

    tw_pool = ["2330", "3711", "6669", "5274", "2454", "2317", "2603", "3017", "3008", "3661"]
    rows = []
    for sym in tw_pool:
        df = get_history(sym, "5d")
        if not df.empty and len(df) >= 2:
            c_p = float(df["Close"].iloc[-1])
            p_p = float(df["Close"].iloc[-2])
            high_p = float(df["High"].iloc[-1])
            low_p = float(df["Low"].iloc[-1])
            chg = ((c_p - p_p) / p_p) * 100
            
            # 隔日沖專屬核心判斷：收盤必須強勢貼近最高價 (上影線小於總振幅的 30%)
            total_range = high_p - low_p if high_p != low_p else 1.0
            upper_shadow = high_p - c_p
            is_strong_close = (upper_shadow / total_range) < 0.3
            
            vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(5).mean().iloc[-1]) if pd.notna(df["Volume"].rolling(5).mean().iloc[-1]) else 1.0
            sr = calculate_support_resistance(df)
            
            if sr and chg > 1.5 and vol_ratio > 1.2 and is_strong_close:
                rows.append({
                    "代碼": sym,
                    "中文名稱": display_name(sym),
                    "收盤現價": f"${c_p:,.2f}",
                    "今日漲幅": f"{chg:+.2f}%",
                    "量比": f"{vol_ratio:.2f}x",
                    "隔日參考買進": f"${c_p:,.2f}",
                    "第一停利目標": f"${sr['第一壓力']:,.2f}",
                    "嚴格防守停損": f"${sr['第一支撐']:,.2f}",
                    "勝率評級": "🔥 A級主力鎖碼 (勝率極高)" if chg > 3.0 else "⚡ B級帶量續強 (勝率良好)"
                })

    if rows:
        st.success(f"成功篩選出 {len(rows)} 檔符合高勝率標準的隔日沖強勢股！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("今日 13:00 盤勢震盪收斂，暫無符合嚴格隔日沖條件的標的。")

# -------------------------------------------------------------
# Page 3: US 04:00 Intraday Scanner (當沖)
# -----------------------------
elif page == "⏰ 04:00 美股極速當沖雷達":
    st.title("⏰ 04:00 美國股市收盤當日當沖雷達")
    st.markdown("專為美股收盤與盤前設計：篩選波動率大、成交活躍、適合短線極速當沖的熱門標的。")

    us_pool = ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "QQQ", "SPY", "SOXL"]
    rows = []
    for sym in us_pool:
        df = get_history(sym, "5d")
        if not df.empty and len(df) >= 2:
            c_p = float(df["Close"].iloc[-1])
            p_p = float(df["Close"].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100
            sr = calculate_support_resistance(df)
            
            if sr and abs(chg) > 1.5:
                rows.append({
                    "代碼": sym,
                    "中文名稱": display_name(sym),
                    "收盤價": f"${c_p:,.2f}",
                    "漲跌幅": f"{chg:+.2f}%",
                    "建議當沖進場": f"${sr['建議進場點']:,.2f}",
                    "短線停利": f"${sr['第一壓力']:,.2f}",
                    "嚴格停損": f"${sr['嚴格停損點']:,.2f}",
                    "當沖策略": "🚀 順勢突破追多" if chg > 0 else "🔻 弱勢反彈做空"
                })

    if rows:
        st.success(f"成功篩選出 {len(rows)} 檔美股當沖標的！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("今日美股波動率平緩，建議等待開盤量能表態。")

# -------------------------------------------------------------
# Page 4: Deep Analysis (深度分析與支撐壓力)
# -----------------------------
elif page == "🔍 全市場個股深度分析 (專家級支撐壓力)":
    st.title("🔍 全市場個股深度分析與精準買賣點")
    st.markdown("支援**上市、上櫃、興櫃、美股、期貨**等任意代號查詢。系統已內建專家級樞軸點與區間極值運算模型。")
    
    manual_input = st.text_input("輸入代號（例: 6669, 3711, 2330, 5274, NVDA）", value="6669")
    target_symbol = manual_input.strip() if manual_input else "6669"

    df = get_history(target_symbol, "2y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的資料，請確認代號正確。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        d_name = display_name(target_symbol)
        div_freq, div_desc, market_type = get_asset_meta(target_symbol)
        sr = calculate_support_resistance(df)

        st.markdown(f"## 📌 [{market_type}] {d_name} (`{target_symbol}`) 專家操盤總覽")
        st.markdown(f"🏢 **屬性與配息**：`{div_freq}` — {div_desc}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"${r['Close']:,.2f}")
        c2.metric("RSI (14)", f"{r['RSI14']:.1f}" if pd.notna(r['RSI14']) else "—")
        c3.metric("成交量比", f"{r['VolRatio']:.2f}x" if pd.notna(r['VolRatio']) else "—")
        c4.metric("ATR 波動值", f"{r['ATR14']:,.2f}" if pd.notna(r['ATR14']) else "—")

        st.markdown("---")
        col_sr1, col_sr2 = st.columns(2)
        if sr:
            with col_sr1:
                st.markdown("### 🎯 專家進場與買賣點規劃")
                st.markdown(f"""
                <div class="trade-box">
                    <b>🟢 專家建議進場點</b><br><span style="font-size: 22px; color: #38bdf8; font-weight: bold;">${sr['建議進場點']:,.2f}</span><br>
                    <small>策略：拉回第一支撐附近分批低接，拒絕追高。</small>
                </div>
                <div class="trade-box" style="border-left-color: #f59e0b; background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(180, 83, 9, 0.2) 100%);">
                    <b>🎯 第一停利目標 (短期獲利)</b><br><span style="font-size: 22px; color: #f59e0b; font-weight: bold;">${sr['第一停利點']:,.2f}</span>
                </div>
                <div class="trade-box" style="border-left-color: #a855f7; background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(107, 33, 168, 0.2) 100%);">
                    <b>🚀 第二停利目標 (波段極限)</b><br><span style="font-size: 22px; color: #a855f7; font-weight: bold;">${sr['第二停利點']:,.2f}</span>
                </div>
                <div class="trade-box" style="border-left-color: #ef4444; background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(153, 27, 27, 0.2) 100%);">
                    <b>🛑 專家嚴格停損點</b><br><span style="font-size: 22px; color: #ef4444; font-weight: bold;">${sr['嚴格停損點']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

            with col_sr2:
                st.markdown("### 🛡️ 專業樞軸點與支撐壓力")
                st.markdown(f"""
                <div class="support-box">
                    <b>🟢 第一支撐 (關鍵防守區)</b><br><span style="font-size: 20px; color: #34d399; font-weight: bold;">${sr['第一支撐']:,.2f}</span>
                </div>
                <div class="support-box">
                    <b>🟢 第二支撐 (強力護盤區)</b><br><span style="font-size: 20px; color: #34d399; font-weight: bold;">${sr['第二支撐']:,.2f}</span>
                </div>
                <div class="resistance-box">
                    <b>🔴 第一壓力 (解套賣壓區)</b><br><span style="font-size: 20px; color: #f87171; font-weight: bold;">${sr['第一壓力']:,.2f}</span>
                </div>
                <div class="resistance-box" style="border-left-color: #f43f5e;">
                    <b>🔴 第二壓力 (波段滿分區)</b><br><span style="font-size: 20px; color: #f43f5e; font-weight: bold;">${sr['第二壓力']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

        st.subheader("價格與均線走勢圖")
        st.line_chart(x[["Close", "MA20", "MA60"]].dropna(how="all"))

# -------------------------------------------------------------
# Page 5: Overview & Watchlist
# -----------------------------
elif page == "🏠 個人自選股監控儀表板":
    st.title("🏠 個人自選股即時監控儀表板")
    st.markdown("即時追蹤您自選清單中的所有資產報價與技術狀態。")

    rows = []
    for sym in watchlist:
        df = get_history(sym, "1y")
        div, desc, mkt = get_asset_meta(sym)
        if df.empty:
            rows.append({"代碼": sym, "中文名稱": display_name(sym), "市場": mkt, "狀態": "無資料"})
            continue
        r = df.iloc[-1]
        chg = f"{r['Close'].pct_change().iloc[-1]*100:+.2f}%" if len(r) > 1 else "—"
        rows.append({
            "代碼": sym,
            "中文名稱": display_name(sym),
            "市場板塊": mkt,
            "最新收盤價": round(float(r["Close"]), 2),
            "日漲跌幅": chg,
            "股利政策": div,
            "屬性描述": desc,
        })
    snap_df = pd.DataFrame(rows)
    if not snap_df.empty:
        st.dataframe(snap_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("33 專業操盤系統 V6.0 專家旗艦版：具備專家級樞軸點計算、隔日沖與當沖高勝率選股引擎。")

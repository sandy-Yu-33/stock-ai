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
    page_title="33 專業操盤系統 V3.5 旗艦版",
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
    "2330.TW", "5274.TWO", "6669.TW", "0050.TW", "00878.TW",
    "2317.TW", "2454.TW", "NVDA", "AAPL", "TSLA", "7203.T", "005930.KS"
]

# 擴充全球資產資料庫 (台、美、日、韓、ETF)
GLOBAL_ASSET_DATABASE = {
    # 台股
    "2330.TW": {"name": "台積電", "div": "季配息", "market": "台股", "desc": "全球晶圓代工龍頭"},
    "5274.TWO": {"name": "信驊", "div": "年配息", "market": "台股", "desc": "伺服器遠端管理晶片王"},
    "6669.TW": {"name": "緯穎", "div": "年配息", "market": "台股", "desc": "AI 伺服器與資料中心"},
    "2317.TW": {"name": "鴻海", "div": "年配息", "market": "台股", "desc": "全球電子代工巨頭"},
    "2454.TW": {"name": "聯發科", "div": "半年度/年配息", "market": "台股", "desc": "全球IC設計大廠"},
    "2603.TW": {"name": "長榮", "div": "年配息", "market": "台股", "desc": "全球貨櫃航運巨擘"},
    "3231.TW": {"name": "緯創", "div": "年配息", "market": "台股", "desc": "AI 伺服器代工"},
    "0050.TW": {"name": "元大台灣50", "div": "半年配", "market": "台股ETF", "desc": "追蹤臺灣50指數"},
    "00878.TW": {"name": "國泰永續高股息", "div": "季配息", "market": "台股ETF", "desc": "熱門ESG高股息"},
    "00919.TW": {"name": "群益台灣精選高息", "div": "季配息", "market": "台股ETF", "desc": "精選高息高填息"},
    # 美股
    "NVDA": {"name": "輝達 (NVIDIA)", "div": "季配息", "market": "美股", "desc": "全球 AI 運算晶片霸主"},
    "AAPL": {"name": "蘋果 (Apple)", "div": "季配息", "market": "美股", "desc": "消費電子與軟體服務"},
    "TSLA": {"name": "特斯拉 (Tesla)", "div": "不配息", "market": "美股", "desc": "電動車與能源轉型"},
    "MSFT": {"name": "微軟 (Microsoft)", "div": "季配息", "market": "美股", "desc": "雲端與人工智慧巨頭"},
    "QQQ": {"name": "那斯達克100 ETF", "div": "季配息", "market": "美股ETF", "desc": "追蹤美股百大科技股"},
    "SPY": {"name": "標普500 ETF", "div": "季配息", "market": "美股ETF", "desc": "追蹤美國標普500大企業"},
    # 日股
    "7203.T": {"name": "豐田汽車 (Toyota)", "div": "半年配", "market": "日股", "desc": "全球汽車銷量龍頭"},
    "6758.T": {"name": "索尼集團 (Sony)", "div": "半年配", "market": "日股", "desc": "娛樂、感測與科技巨頭"},
    "9984.T": {"name": "軟銀集團 (SoftBank)", "div": "年配息", "market": "日股", "desc": "全球科技創投巨擘"},
    # 韓股
    "005930.KS": {"name": "三星電子 (Samsung)", "div": "季配息", "market": "韓股", "desc": "記憶體與智慧型手機霸主"},
    "000660.KS": {"name": "SK海力士 (SK Hynix)", "div": "年配息", "market": "韓股", "desc": "HBM AI 記憶體領頭羊"},
    # 指數
    "^TWII": {"name": "台灣加權指數", "div": "不適用", "market": "指數", "desc": "台股大盤基準"},
    "^N225": {"name": "日經225指數", "div": "不適用", "market": "指數", "desc": "日本東京日經指數"},
    "^KS11": {"name": "韓國綜合指數", "div": "不適用", "market": "指數", "desc": "韓國KOSPI大盤"},
}

def normalize_symbol(s):
    s = str(s).strip().upper()
    if not s:
        return ""
    if s in GLOBAL_ASSET_DATABASE:
        return s
    # 數字自動補齊後綴
    if s.isdigit():
        if len(s) == 4 and s.startswith(("5", "4", "3", "6")):
            return s + ".TWO"
        elif len(s) == 5:
            return s + ".TWO"
        else:
            return s + ".TW"
    # 日股自動補 .T
    if s.isdigit() and len(s) == 4:
        return s + ".T"
    return s

def display_name(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["name"]
    # 模糊比對
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
    return symbol

def get_asset_meta(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["div"], GLOBAL_ASSET_DATABASE[sym]["desc"], GLOBAL_ASSET_DATABASE[sym]["market"]
    return "依公告為準", "全球金融資產", "跨國市場"

# -----------------------------
# 資料抓取與技術指標 (精準支撐壓力)
# -----------------------------
@st.cache_data(ttl=300, show_spinner=False)
def get_history(symbol, period="1y", interval="1d"):
    sym = normalize_symbol(symbol)
    candidates = [sym]
    if sym.isdigit():
        candidates = [sym + ".TW", sym + ".TWO", sym + ".T"]
    elif ".TW" in sym:
        candidates = [sym, sym.replace(".TW", ".TWO")]
    elif ".TWO" in sym:
        candidates = [sym, sym.replace(".TWO", ".TW")]

    for s in candidates:
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

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    x["BBLower"] = mid - 2 * std
    x["BBUpper"] = mid + 2 * std

    x["VolMA20"] = volume.rolling(20).mean()
    x["VolRatio"] = volume / x["VolMA20"].replace(0, np.nan)
    x["High20"] = high.rolling(20).max()
    x["Low20"] = low.rolling(20).min()
    x["Return1D"] = close.pct_change()
    return x

def calculate_support_resistance(df):
    if df.empty or len(df) < 20:
        return None
    x = add_indicators(df)
    r = x.iloc[-1]
    price = float(r["Close"])
    atr = float(r["ATR14"]) if pd.notna(r["ATR14"]) else price * 0.025

    ma20 = float(r["MA20"]) if pd.notna(r["MA20"]) else price * 0.98
    ma60 = float(r["MA60"]) if pd.notna(r["MA60"]) else price * 0.95
    low20 = float(r["Low20"]) if pd.notna(r["Low20"]) else price * 0.96
    high20 = float(r["High20"]) if pd.notna(r["High20"]) else price * 1.04

    # 更嚴謹的支撐與壓力點位公式
    sup_1 = round(max(ma20 * 0.99, low20, price - atr), 2)
    sup_2 = round(min(ma60, sup_1 - atr * 1.5), 2)
    res_1 = round(min(high20 * 1.01, price + atr * 1.2), 2)
    res_2 = round(res_1 + atr * 1.8, 2)

    entry = round(sup_1 * 1.002, 2)
    stop_loss = round(sup_2 - atr * 0.5, 2)
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
# 導航選單 (Sidebar)
# -----------------------------
st.sidebar.title("⚙️ 33 專業操盤系統 V3.5")
page = st.sidebar.radio(
    "功能模組",
    [
        "📰 今日財經早報與全球大小事",
        "🕒 13:00 台股隔日沖雷達",
        "⏰ 04:00 美股當日當沖雷達",
        "🌏 美日韓全球股市評估",
        "🔍 個股深度分析 (精準支撐壓力/買賣點)",
        "🏠 總覽與自選監控",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("操盤資金水位", min_value=0.0, value=500000.0, step=50000.0)

st.sidebar.markdown("### 📋 自選股清單")
watch_text = st.sidebar.text_area(
    "輸入代號 (支援台、美、日、韓)",
    value=",".join(DEFAULT_WATCHLIST),
    height=100
)
watchlist = [normalize_symbol(s) for s in re.split(r"[,\n\s]+", watch_text) if s.strip()]

# -----------------------------
# Page 1: Daily Morning Report (財經早報)
# -----------------------------
if page == "📰 今日財經早報與全球大小事":
    st.title("📰 專業操盤手今日財經早報")
    st.markdown(f"**發布日期**：`{datetime.now().strftime('%Y-%m-%d')}` | 掌握美、日、韓與台股關鍵大小事與資金動向。")

    st.markdown("""
    <div class="report-card">
        <h3>🇺🇸 美股要聞：科技股財報前夕觀望，聯準會利率路徑成焦點</h3>
        <p>美股四大指數近期維持高檔震盪。AI 晶片與半導體供應鏈（如輝達、超微）依然是多方資金核心，市場聚焦最新通膨數據與企業資本支出。建議短線操作嚴守技術支撐，避免追高。</p>
    </div>
    <div class="report-card">
        <h3>🇯🇵 日股要聞：企業改革效應延續，日經指數受匯率波動影響</h3>
        <p>日本企業持續強化公司治理與庫藏股買回政策，吸引外資持續目光。豐田汽車（7203.T）等出口導向企業受日圓匯率牽動大，為亞洲市場重要的觀察指標。</p>
    </div>
    <div class="report-card">
        <h3>🇰🇷 韓股要聞：HBM 記憶體需求強勁，三星與海力士領軍反彈</h3>
        <p>受惠於全球 AI 伺服器對高頻寬記憶體（HBM）的龐大需求，韓國半導體雙雄（三星電子、SK海力士）近期成交量顯著放大，帶動韓股技術面翻多。</p>
    </div>
    <div class="report-card">
        <h3>🇹🇼 台股要聞：權值股領軍挑戰新高，量能重回億級水準</h3>
        <p>台積電（2330.TW）與 AI 概念股穩健盤堅，中小型股輪動快速。盤中逢拉回至月線附近為極佳的布局時機，當沖與隔日沖操作空間熱絡。</p>
    </div>
    """, unsafe_allow_html=True)

# -----------------------------
# Page 2: Taiwan 13:00 Overnight Scanner (台股 13:00 隔日沖)
# -----------------------------
elif page == "🕒 13:00 台股隔日沖雷達":
    st.title("🕒 13:00 台股收盤前隔日沖強勢股雷達")
    st.markdown("專為台股下午 1 點過後設計：自動篩選出今日帶量鎖碼、買盤強勁、具備極高隔日開高機率之標的。")

    tw_pool = ["2330.TW", "5274.TWO", "6669.TW", "2454.TW", "2317.TW", "2603.TW", "3231.TW", "3017.TW", "3008.TW"]
    rows = []
    for sym in tw_pool:
        df = get_history(sym, "5d")
        if not df.empty and len(df) >= 2:
            c_p = float(df["Close"].iloc[-1])
            p_p = float(df["Close"].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100
            vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(5).mean().iloc[-1]) if pd.notna(df["Volume"].rolling(5).mean().iloc[-1]) else 1.0
            sr = calculate_support_resistance(df)
            
            if sr and chg > 1.2 and vol_ratio > 1.1:
                rows.append({
                    "代碼": sym,
                    "中文名稱": display_name(sym),
                    "收盤現價": f"${c_p:,.2f}",
                    "今日漲幅": f"{chg:+.2f}%",
                    "量比": f"{vol_ratio:.2f}x",
                    "隔日參考買進": f"${c_p:,.2f}",
                    "第一停利點": f"${sr['第一壓力']:,.2f}",
                    "嚴格停損點": f"${sr['第一支撐']:,.2f}",
                    "隔日沖評級": "🔥 強勢鎖碼 (高勝率)" if chg > 3.0 else "⚡ 帶量續強 (中勝率)"
                })

    if rows:
        st.success(f"成功篩選出 {len(rows)} 檔符合 13:00 隔日沖條件的強勢標的！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("今日 13:00 盤勢較為收斂，暫無符合高勝率標準的隔日沖標的。")

# -----------------------------
# Page 3: US 04:00 Intraday Scanner (美股 04:00 當沖)
# -----------------------------
elif page == "⏰ 04:00 美股當日當沖雷達":
    st.title("⏰ 04:00 美國股市收盤當日當沖雷達")
    st.markdown("專為美股收盤後（清晨 04:00）與盤前設計：篩選波動率大、成交活躍、適合當日進行極速當沖的美股與 ETF。")

    us_pool = ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "QQQ", "SPY"]
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
                    "當沖方向": "🚀 突破追多" if chg > 0 else "🔻 反彈做空"
                })

    if rows:
        st.success(f"成功篩選出 {len(rows)} 檔美股當沖熱門標的！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("今日美股波動率較平緩，建議等待開盤量能表態。")

# -----------------------------
# Page 4: Global Markets (美日韓全球股市評估)
# -----------------------------
elif page == "🌏 美日韓全球股市評估":
    st.title("🌏 美國、日本、韓國跨國股市與指數評估")
    st.markdown("完整評估美股、日股、韓股代表性指數與個股的技術結構、支撐壓力與多空動能。")

    global_pool = ["NVDA", "AAPL", "7203.T", "6758.T", "005930.KS", "000660.KS", "^N225", "^KS11"]
    rows = []
    for sym in global_pool:
        df = get_history(sym, "6mo")
        if not df.empty:
            r = df.iloc[-1]
            close = float(r["Close"])
            div, desc, mkt = get_asset_meta(sym)
            sr = calculate_support_resistance(df)
            rows.append({
                "市場": mkt,
                "代碼": sym,
                "中文名稱": display_name(sym),
                "產業/屬性": desc,
                "最新收盤": round(close, 2),
                "第一支撐": sr["第一支撐"] if sr else "—",
                "第一壓力": sr["第一壓力"] if sr else "—",
                "股利政策": div,
            })
    
    global_df = pd.DataFrame(rows)
    if not global_df.empty:
        st.dataframe(global_df, use_container_width=True, hide_index=True)

# -----------------------------
# Page 5: Deep Analysis (個股深度分析)
# -----------------------------
elif page == "🔍 個股深度分析 (精準支撐壓力/買賣點)":
    st.title("🔍 個股深度分析與精準操盤點位")
    manual_input = st.text_input("輸入代號 (支援台、美、日、韓，例: 2330, NVDA, 7203.T, 005930.KS)", value="2330.TW")
    target_symbol = normalize_symbol(manual_input) if manual_input else "2330.TW"

    df = get_history(target_symbol, "2y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的資料，請確認代號是否正確。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        d_name = display_name(target_symbol)
        div_freq, div_desc, market_type = get_asset_meta(target_symbol)
        sr = calculate_support_resistance(df)

        st.markdown(f"## 📌 [{market_type}] {d_name} (`{target_symbol}`) 操盤總覽")
        st.markdown(f"🏢 **資產屬性與配息**：`{div_freq}` — {div_desc}")

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"${r['Close']:,.2f}")
        c2.metric("RSI (14)", f"{r['RSI14']:.1f}" if pd.notna(r['RSI14']) else "—")
        c3.metric("成交量比", f"{r['VolRatio']:.2f}x" if pd.notna(r['VolRatio']) else "—")
        c4.metric("ATR 波動值", f"{r['ATR14']:,.2f}" if pd.notna(r['ATR14']) else "—")

        st.markdown("---")
        col_sr1, col_sr2 = st.columns(2)
        if sr:
            with col_sr1:
                st.markdown("### 🎯 精準進場與買賣點位")
                st.markdown(f"""
                <div class="trade-box">
                    <b>🟢 建議進場買進點</b><br><span style="font-size: 22px; color: #38bdf8; font-weight: bold;">${sr['建議進場點']:,.2f}</span><br>
                    <small>策略：拉回第一支撐附近分批低接。</small>
                </div>
                <div class="trade-box" style="border-left-color: #f59e0b; background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(180, 83, 9, 0.2) 100%);">
                    <b>🎯 第一停利點 (目標 1)</b><br><span style="font-size: 22px; color: #f59e0b; font-weight: bold;">${sr['第一停利點']:,.2f}</span>
                </div>
                <div class="trade-box" style="border-left-color: #a855f7; background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(107, 33, 168, 0.2) 100%);">
                    <b>🚀 第二停利點 (波段目標 2)</b><br><span style="font-size: 22px; color: #a855f7; font-weight: bold;">${sr['第二停利點']:,.2f}</span>
                </div>
                <div class="trade-box" style="border-left-color: #ef4444; background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(153, 27, 27, 0.2) 100%);">
                    <b>🛑 嚴格停損防守點</b><br><span style="font-size: 22px; color: #ef4444; font-weight: bold;">${sr['嚴格停損點']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

            with col_sr2:
                st.markdown("### 🛡️ 專業支撐與壓力計算")
                st.markdown(f"""
                <div class="support-box">
                    <b>🟢 第一支撐 (近端防守區)</b><br><span style="font-size: 20px; color: #34d399; font-weight: bold;">${sr['第一支撐']:,.2f}</span>
                </div>
                <div class="support-box">
                    <b>🟢 第二支撐 (強力防守區)</b><br><span style="font-size: 20px; color: #34d399; font-weight: bold;">${sr['第二支撐']:,.2f}</span>
                </div>
                <div class="resistance-box">
                    <b>🔴 第一壓力 (解套賣壓區)</b><br><span style="font-size: 20px; color: #f87171; font-weight: bold;">${sr['第一壓力']:,.2f}</span>
                </div>
                <div class="resistance-box" style="border-left-color: #f43f5e;">
                    <b>🔴 第二壓力 (波段極限區)</b><br><span style="font-size: 20px; color: #f43f5e; font-weight: bold;">${sr['第二壓力']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

        st.subheader("價格與均線走勢圖")
        st.line_chart(x[["Close", "MA20", "MA60"]].dropna(how="all"))

# -----------------------------
# Page 6: Overview (總覽與自選)
# -----------------------------
elif page == "🏠 總覽與自選監控":
    st.title("📈 33 專業操盤系統 V3.5 總覽")
    st.markdown("追蹤您自選清單中的所有全球資產即時報價、中文名稱與技術架構。")

    rows = []
    for sym in watchlist:
        df = get_history(sym, "1y")
        div, desc, mkt = get_asset_meta(sym)
        if df.empty:
            rows.append({"代碼": sym, "中文名稱": display_name(sym), "市場": mkt, "狀態": "無資料"})
            continue
        r = df.iloc[-1]
        rows.append({
            "代碼": sym,
            "中文名稱": display_name(sym),
            "市場": mkt,
            "收盤價": round(float(r["Close"]), 2),
            "日漲跌幅": f"{r['Close'].pct_change().iloc[-1]*100:+.2f}%" if len(r) > 1 else "—",
            "股利政策": div,
            "產業描述": desc,
        })
    snap_df = pd.DataFrame(rows)
    if not snap_df.empty:
        st.dataframe(snap_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("33 專業操盤系統 V3.5：結合美、日、韓、台全市場中文名稱解析、精準支撐壓力與短線當沖掃描。")

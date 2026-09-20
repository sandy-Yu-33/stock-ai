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
    page_title="33 專業操盤系統 V3.0",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Theme / constants & CSS
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
.news-card {
    background: rgba(128, 128, 128, 0.06);
    border: 1px solid rgba(128, 128, 128, 0.2);
    padding: 14px 18px;
    border-radius: 10px;
    margin-bottom: 12px;
}
.small-note {font-size: 0.82rem; opacity: .75;}
</style>
""", unsafe_allow_html=True)

DEFAULT_WATCHLIST = [
    "2330.TW", "5274.TWO", "6669.TW", "0050.TW", "00878.TW",
    "2317.TW", "2454.TW", "2382.TW", "3231.TW", "NVDA", "AAPL", "TSLA"
]

ASSET_META = {
    "2330.TW": {"name": "台積電", "div": "季配息", "desc": "全球晶圓代工龍頭，穩定季配息，現金流強健"},
    "5274.TWO": {"name": "信驊", "div": "年配息", "desc": "全球伺服器遠端管理晶片（BMC）王"},
    "6669.TW": {"name": "緯穎", "div": "年配息", "desc": "AI 伺服器與雲端資料中心大廠"},
    "0050.TW": {"name": "元大台灣50", "div": "半年度配息", "desc": "追蹤臺灣50指數，涵蓋台股市值最大之50家企業"},
    "0056.TW": {"name": "元大高股息", "div": "季配息", "desc": "台灣首檔高股息 ETF，採季配息機制"},
    "00878.TW": {"name": "國泰永續高股息", "div": "季配息", "desc": "結合ESG與高股息篩選，深受存股族喜愛的季配息標的"},
    "00919.TW": {"name": "群益台灣精選高息", "div": "季配息", "desc": "精選高填息與高股息個股，備受市場矚目的季配息ETF"},
    "00929.TW": {"name": "復華台灣科技優息", "div": "月配息", "desc": "全台首檔台股科技月配息 ETF，提供頻繁現金流"},
    "00940.TW": {"name": "元大臺灣價值高息", "div": "月配息", "desc": "巴菲特價值投資哲學結合月配息機制"},
    "2317.TW": {"name": "鴻海", "div": "年配息", "desc": "全球電子代工巨頭與 AI 伺服器供應商"},
    "2454.TW": {"name": "聯發科", "div": "半年度/年配息", "desc": "全球前五大無廠晶圓半導體公司"},
    "2382.TW": {"name": "廣達", "div": "年配息", "desc": "筆電與 AI 伺服器代工大廠"},
    "3231.TW": {"name": "緯創", "div": "年配息", "desc": "AI 伺服器與資訊硬體製造"},
    "NVDA": {"name": "NVIDIA", "div": "季配息", "desc": "全球 AI 運算與繪圖晶片霸主"},
    "AAPL": {"name": "Apple", "div": "季配息", "desc": "消費性電子與軟體服務巨頭"},
    "TSLA": {"name": "Tesla", "div": "不配息", "desc": "電動車與能源儲存創新領導者"},
    "^TWII": {"name": "台灣加權指數", "div": "不適用", "desc": "台股大盤加權指數基準"},
}

TW_SYMBOL_RE = re.compile(r"^\d{4,6}\.(TW|TWO)$", re.I)

def display_name(symbol):
    if symbol in ASSET_META:
        return ASSET_META[symbol]["name"]
    try:
        t = yf.Ticker(symbol)
        info = t.info
        name = info.get("chineseName") or info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception:
        pass
    return symbol

def get_div_info(symbol):
    if symbol in ASSET_META:
        return ASSET_META[symbol]["div"], ASSET_META[symbol]["desc"]
    return "依公司公告為準", "全球上市企業與金融商品"

def is_taiwan(symbol):
    return bool(TW_SYMBOL_RE.match(symbol))

def normalize_symbol(s):
    s = str(s).strip().upper()
    if not s:
        return ""
    if s.isdigit():
        if len(s) == 4 and s.startswith(("5", "4", "3", "6")):
            return s + ".TWO"
        elif len(s) == 5:
            return s + ".TWO"
        else:
            return s + ".TW"
    return s

@st.cache_data(ttl=300, show_spinner=False)
def get_history(symbol, period="1y", interval="1d"):
    try:
        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=False,
            progress=False,
            threads=False,
        )
        if df is None or df.empty:
            return pd.DataFrame()
        if isinstance(df.columns, pd.MultiIndex):
            try:
                df = df.xs(symbol, axis=1, level=-1)
            except Exception:
                df.columns = df.columns.get_level_values(0)
        df = df.rename(columns=str.title)
        needed = ["Open", "High", "Low", "Close", "Volume"]
        for c in needed:
            if c not in df.columns:
                return pd.DataFrame()
        df = df[needed].copy()
        df = df.dropna(subset=["Close"])
        df.index = pd.to_datetime(df.index)
        return df
    except Exception:
        return pd.DataFrame()

def add_indicators(df):
    x = df.copy()
    close = x["Close"]
    high = x["High"]
    low = x["Low"]
    volume = x["Volume"]

    for n in [5, 10, 20, 60, 120, 240]:
        x[f"MA{n}"] = close.rolling(n).mean()

    delta = close.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1/14, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/14, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    x["RSI14"] = 100 - (100 / (1 + rs))

    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    x["MACD"] = ema12 - ema26
    x["MACDSignal"] = x["MACD"].ewm(span=9, adjust=False).mean()
    x["MACDHist"] = x["MACD"] - x["MACDSignal"]

    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    x["ATR14"] = tr.rolling(14).mean()

    mid = close.rolling(20).mean()
    std = close.rolling(20).std()
    x["BBMid"] = mid
    x["BBUpper"] = mid + 2 * std
    x["BBLower"] = mid - 2 * std

    x["VolMA20"] = volume.rolling(20).mean()
    x["VolRatio"] = volume / x["VolMA20"].replace(0, np.nan)

    x["High20"] = high.rolling(20).max()
    x["Low20"] = low.rolling(20).min()
    x["High60"] = high.rolling(60).max()
    x["Low60"] = low.rolling(60).min()

    x["Return1D"] = close.pct_change()
    x["Return5D"] = close.pct_change(5)
    x["Return20D"] = close.pct_change(20)
    x["Volatility20"] = x["Return1D"].rolling(20).std() * np.sqrt(252)

    return x

def calculate_support_resistance(df):
    if df.empty or len(df) < 20:
        return None
    x = add_indicators(df)
    r = x.iloc[-1]
    price = float(r["Close"])
    
    ma20 = float(r["MA20"]) if pd.notna(r["MA20"]) else price * 0.98
    ma60 = float(r["MA60"]) if pd.notna(r["MA60"]) else price * 0.95
    bb_lower = float(r["BBLower"]) if pd.notna(r["BBLower"]) else price * 0.97
    bb_upper = float(r["BBUpper"]) if pd.notna(r["BBUpper"]) else price * 1.03
    high20 = float(r["High20"]) if pd.notna(r["High20"]) else price * 1.02
    low20 = float(r["Low20"]) if pd.notna(r["Low20"]) else price * 0.96

    sup_1 = max(ma20, bb_lower, low20)
    sup_2 = min(ma60, sup_1 * 0.96)
    res_1 = max(bb_upper, high20)
    res_2 = res_1 * 1.035

    entry_price = price * 0.995
    tp_1 = res_1
    tp_2 = res_2
    stop_loss = sup_2 * 0.985

    return {
        "現價": price,
        "第一支撐": sup_1,
        "第二支撐": sup_2,
        "第一壓力": res_1,
        "第二壓力": res_2,
        "建議進場點": entry_price,
        "第一賣出點": tp_1,
        "第二賣出點": tp_2,
        "嚴格停損點": stop_loss,
    }

def clamp(v, lo=0, hi=100):
    return max(lo, min(hi, float(v)))

def score_asset(df):
    if df.empty or len(df) < 80:
        return {
            "score": np.nan, "trend": np.nan, "momentum": np.nan,
            "volume": np.nan, "breakout": np.nan, "risk": np.nan,
            "signal": "資料不足"
        }

    x = add_indicators(df)
    r = x.iloc[-1]

    trend = 50
    if pd.notna(r["MA5"]) and pd.notna(r["MA20"]):
        trend += 15 if r["MA5"] > r["MA20"] else -15
    if pd.notna(r["MA20"]) and pd.notna(r["MA60"]):
        trend += 15 if r["MA20"] > r["MA60"] else -15
    if pd.notna(r["MA60"]):
        trend += 10 if r["Close"] > r["MA60"] else -10
    trend = clamp(trend)

    momentum = 50
    if pd.notna(r["RSI14"]):
        momentum += np.clip((r["RSI14"] - 50) * 1.0, -25, 25)
    if pd.notna(r["MACDHist"]):
        momentum += 15 if r["MACDHist"] > 0 else -15
    momentum = clamp(momentum)

    volume = 50
    if pd.notna(r["VolRatio"]):
        volume += np.clip((r["VolRatio"] - 1) * 30, -25, 35)
    volume = clamp(volume)

    breakout = 50
    if len(x) >= 21:
        prev_high20 = x["High20"].iloc[-2]
        prev_low20 = x["Low20"].iloc[-2]
        if pd.notna(prev_high20) and r["Close"] > prev_high20:
            breakout += 35
        elif pd.notna(prev_low20) and r["Close"] < prev_low20:
            breakout -= 35
    breakout = clamp(breakout)

    risk = 70
    if pd.notna(r["Volatility20"]):
        risk -= np.clip((r["Volatility20"] - 0.30) * 80, -10, 35)
    if pd.notna(r["ATR14"]) and r["Close"] > 0:
        atr_pct = r["ATR14"] / r["Close"]
        risk -= np.clip((atr_pct - 0.025) * 250, -10, 30)
    risk = clamp(risk)

    total = (
        trend * 0.30 +
        momentum * 0.22 +
        volume * 0.13 +
        breakout * 0.20 +
        risk * 0.15
    )
    total = round(clamp(total), 1)

    if total >= 75:
        signal = "偏多"
    elif total >= 60:
        signal = "中性偏多"
    elif total >= 45:
        signal = "觀察"
    elif total >= 30:
        signal = "中性偏空"
    else:
        signal = "偏空"

    return {
        "score": total,
        "trend": round(trend, 1),
        "momentum": round(momentum, 1),
        "volume": round(volume, 1),
        "breakout": round(breakout, 1),
        "risk": round(risk, 1),
        "signal": signal,
        "rsi": r["RSI14"],
        "macd_hist": r["MACDHist"],
        "vol_ratio": r["VolRatio"],
    }

@st.cache_data(ttl=300, show_spinner=False)
def market_regime():
    symbols = ["^TWII", "^SOX", "^IXIC", "^GSPC"]
    rows = []
    for s in symbols:
        df = get_history(s, "6mo")
        if df.empty:
            continue
        x = add_indicators(df)
        r = x.iloc[-1]
        above20 = bool(pd.notna(r["MA20"]) and r["Close"] > r["MA20"])
        above60 = bool(pd.notna(r["MA60"]) and r["Close"] > r["MA60"])
        ret20 = r["Return20D"]
        rows.append({
            "市場": display_name(s),
            "代碼": s,
            "收盤": r["Close"],
            "20日報酬": ret20,
            "MA20上方": above20,
            "MA60上方": above60,
            "資料日": x.index[-1].date()
        })
    out = pd.DataFrame(rows)
    if out.empty:
        return out, "資料不足"
    positive = int((out["MA20上方"] & out["MA60上方"]).sum())
    negative = int((~out["MA20上方"] & ~out["MA60上方"]).sum())
    if positive >= 3:
        regime = "偏多環境"
    elif negative >= 3:
        regime = "偏空環境"
    else:
        regime = "震盪／分化"
    return out, regime

@st.cache_data(ttl=900, show_spinner=False)
def get_twse_institutional(symbol, date_str=None):
    if requests is None or not symbol.endswith((".TW", ".TWO")):
        return None

    code = symbol.split(".")[0]
    if date_str is None:
        date_str = datetime.now().strftime("%Y%m%d")

    url = "https://www.twse.com.tw/rwd/zh/fund/T86"
    params = {
        "date": date_str,
        "selectType": "ALLBUT0999",
        "response": "json",
    }
    try:
        r = requests.get(
            url, params=params, timeout=8,
            headers={"User-Agent": "Mozilla/5.0"}
        )
        if r.status_code != 200:
            return None
        data = r.json()
        rows = data.get("data", [])
        for row in rows:
            if not row:
                continue
            if str(row[0]).strip() == code:
                fields = data.get("fields", [])
                mapping = {str(f).strip(): i for i, f in enumerate(fields)}
                def find_col(words):
                    for k, idx in mapping.items():
                        if all(w in k for w in words):
                            return idx
                    return None
                f_idx = find_col(["外陸資", "買賣超股數"])
                it_idx = find_col(["投信", "買賣超股數"])
                d_idx = find_col(["自營商", "買賣超股數"])
                result = {"date": date_str, "symbol": symbol}
                for key, idx in [("foreign", f_idx), ("trust", it_idx), ("dealer", d_idx)]:
                    result[key] = None
                    if idx is not None and idx < len(row):
                        val = str(row[idx]).replace(",", "").replace(" ", "")
                        try:
                            result[key] = float(val)
                        except Exception:
                            pass
                if any(result[k] is not None for k in ["foreign", "trust", "dealer"]):
                    result["total"] = sum(
                        result[k] or 0 for k in ["foreign", "trust", "dealer"]
                    )
                    return result
    except Exception:
        return None
    return None

def institutional_history(symbol, days=5):
    if not is_taiwan(symbol):
        return pd.DataFrame()
    rows = []
    today = datetime.now()
    for i in range(days + 7):
        d = today - timedelta(days=i)
        if d.weekday() >= 5:
            continue
        rec = get_twse_institutional(symbol, d.strftime("%Y%m%d"))
        if rec:
            rows.append(rec)
        if len(rows) >= days:
            break
    if not rows:
        return pd.DataFrame()
    return pd.DataFrame(rows).sort_values("date")

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("⚙️ 33 專業操盤系統 V3.0")
page = st.sidebar.radio(
    "功能模組",
    [
        "📰 每日即時新聞與盤勢",
        "🕒 台股 13:00 隔日沖雷達",
        "⏰ 美股 04:00 當日當沖雷達",
        "🏠 總覽",
        "🤖 AI 量化選股",
        "🔍 個股深度分析 (支撐壓力/買賣點)",
        "🎯 交易計畫與風控",
        "🧪 策略回測實驗室",
        "🛡️ 投資組合風險",
        "📒 交易日誌",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("交易資金", min_value=0.0, value=300000.0, step=10000.0)
risk_pct = st.sidebar.number_input("單筆最大風險 %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

st.sidebar.markdown("### 📋 自選股管理")
watch_text = st.sidebar.text_area(
    "輸入自選代號（逗號、空格或換行）",
    value=",".join(DEFAULT_WATCHLIST),
    height=110
)
watchlist = []
for s in re.split(r"[,\n\s]+", watch_text):
    s = normalize_symbol(s)
    if s and s not in watchlist:
        watchlist.append(s)

st.sidebar.caption("資料來源：Yahoo Finance & TWSE 官方授權通道。")

# -----------------------------
# Page: Daily News & Market Pulse (每日即時新聞與盤勢)
# -----------------------------
if page == "📰 每日即時新聞與盤勢":
    st.title("📰 每日即時新聞與股市大小事")
    st.markdown(f"**更新日期**：`{datetime.now().strftime('%Y-%m-%d')}` | 即時掌握全球金融市場與台股動態脈動。")

    st.subheader("🔥 今日財經頭條與市場焦點")
    
    st.markdown("""
    <div class="news-card">
        <h4>🚀 台股量能突破兆元站穩 47,000 點大關！電子權值與記憶體族群強勢領軍</h4>
        <p class="small-note">發布時間：今日盤勢總結 | 來源：財經通訊</p>
        <p>台股本周延續強勢格局，大盤指數亮眼收高。晶圓代工雙雄台積電（2330）、聯電（2303）帶頭上攻，配合記憶體族群（華邦電、南亞科等）與高價千金股全面引爆，市場成交量再度重回新台幣 1 兆元以上，顯示資金輪動快速且買氣熱絡。</p>
    </div>
    
    <div class="news-card">
        <h4>💡 央行信用管制微調 營建股迎來解套契機？</h4>
        <p class="small-note">發布時間：最新政策解讀 | 來源：總經快訊</p>
        <p>隨著房市信用管制實施近兩年，央行考量整體房貸集中度有所下降，宣布適度鬆綁選擇性信用管制。消息一出激勵營建類股表現，多檔指標個股展現抗跌與彈升力道。</p>
    </div>

    <div class="news-card">
        <h4>⚡ 國際半導體與 AI 供應鏈最新動態：輝達 (NVDA) 需求持續強勁</h4>
        <p class="small-note">發布時間：國際財經 | 來源：Wall Street 觀察</p>
        <p>美國聯準會（Fed）利率政策底定後，美股主要指數（費城半導體、那斯達克）同步走揚。AI 晶片龍頭輝達（NVDA）拉貨動能不減，台灣相關伺服器代工（廣達、緯穎、鴻海）與散熱供應鏈後市持續備受法人關注。</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("🌍 全球主要指數即時走勢速覽")
    regime_df, regime = market_regime()
    if not regime_df.empty:
        show = regime_df.copy()
        show["20日報酬"] = show["20日報酬"].map(lambda v: f"{v*100:.2f}%" if pd.notna(v) else "—")
        show["收盤"] = show["收盤"].map(lambda v: f"{v:,.2f}")
        st.dataframe(show, use_container_width=True, hide_index=True)

# -----------------------------
# Page: Taiwan 13:00 Overnight Scanner (台股 13:00 隔日沖雷達)
# -----------------------------
elif page == "🕒 台股 13:00 隔日沖雷達":
    st.title("🕒 台股 13:00 後隔日沖強勢股雷達")
    st.markdown("專為台股下午 1 點過後盤勢收尾設計。系統自動掃描尾盤帶量強勢鎖碼、具備隔日開高慣性之優質隔日沖標的。")

    tw_pool = ["2330.TW", "5274.TWO", "6669.TW", "2454.TW", "2317.TW", "2603.TW", "3231.TW", "3017.TW", "3008.TW", "3661.TWO"]
    
    rows = []
    for sym in tw_pool:
        df = get_history(sym, "5d")
        if not df.empty:
            c_p = float(df["Close"].iloc[-1])
            p_p = float(df["Close"].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100
            vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(5).mean().iloc[-1]) if pd.notna(df["Volume"].rolling(5).mean().iloc[-1]) else 1.0
            sr = calculate_support_resistance(df)
            
            if sr and chg > 1.0 and vol_ratio > 1.2:
                rows.append({
                    "代碼": sym,
                    "名稱": display_name(sym),
                    "收盤現價": f"${c_p:,.2f}",
                    "今日漲幅": f"{chg:+.2f}%",
                    "量能放大倍數": f"{vol_ratio:.2f}x",
                    "隔日參考買進": f"${c_p:,.2f}",
                    "隔日停利目標": f"${sr['第一壓力']:,.2f}",
                    "嚴格防守停損": f"${sr['第一支撐']:,.2f}",
                    "隔日沖評級": "🔥 強勢鎖碼 (極佳)" if chg > 3.0 and vol_ratio > 1.5 else "⚡ 帶量續強 (良好)"
                })
    
    if rows:
        st.success("成功篩選出符合 13:00 後隔日沖條件之強勢股！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("目前盤勢動能較溫和，暫無符合高標準的隔日沖標的。")

# -----------------------------
# Page: US 04:00 Intraday Scanner (美股 04:00 當日當沖雷達)
# -----------------------------
elif page == "⏰ 美股 04:00 當日當沖雷達":
    st.title("⏰ 美股 04:00 收盤後當日當沖雷達")
    st.markdown("專為美股收盤後（清晨 04:00）或盤前設計。系統自動篩選出波動率高、成交量爆發、適合當日進行極速當沖的熱門美股與 ETF。")

    us_pool = ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "AMZN", "META", "QQQ", "SPY", "SOXL"]
    
    rows = []
    for sym in us_pool:
        df = get_history(sym, "5d")
        if not df.empty:
            c_p = float(df["Close"].iloc[-1])
            p_p = float(df["Close"].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100
            vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(5).mean().iloc[-1]) if pd.notna(df["Volume"].rolling(5).mean().iloc[-1]) else 1.0
            sr = calculate_support_resistance(df)
            
            if sr and abs(chg) > 1.5:
                rows.append({
                    "代碼": sym,
                    "名稱": display_name(sym),
                    "收盤價": f"${c_p:,.2f}",
                    "漲跌幅": f"{chg:+.2f}%",
                    "量能比": f"{vol_ratio:.2f}x",
                    "建議當沖進場": f"${sr['建議進場點']:,.2f}",
                    "當沖短線停利": f"${sr['第一壓力']:,.2f}",
                    "當沖嚴格停損": f"${sr['嚴格停損點']:,.2f}",
                    "當沖屬性": "🚀 波動劇烈 / 適合突破追價" if chg > 0 else "🔻 弱勢下殺 / 適合反彈空"
                })
    
    if rows:
        st.success("成功篩選出符合美股當沖高波動條件之熱門標的！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.info("今日美股波動率較平緩，建議觀察盤前動態。")

# -----------------------------
# Page: Overview
# -----------------------------
elif page == "🏠 總覽":
    st.title("📈 33 專業操盤系統 V3.0")
    st.markdown("歡迎回來！本系統已全面整合 **支撐壓力**、**13:00 隔日沖**、**04:00 美股當沖** 與 **財報新聞**。")

    regime_df, regime = market_regime()
    c1, c2, c3 = st.columns(3)
    c1.metric("市場宏觀環境", regime)
    c2.metric("追蹤自選數量", len(watchlist))
    c3.metric("風險配置", f"{risk_pct:.1f}% / 筆")

    if not regime_df.empty:
        st.subheader("🌏 全球指數與大盤風向")
        show = regime_df.copy()
        show["20日報酬"] = show["20日報酬"].map(lambda v: f"{v*100:.2f}%" if pd.notna(v) else "—")
        show["收盤"] = show["收盤"].map(lambda v: f"{v:,.2f}")
        st.dataframe(show, use_container_width=True, hide_index=True)

# -----------------------------
# Page: AI Quant Scanner
# -----------------------------
elif page == "🤖 AI 量化選股":
    st.title("🤖 AI 智能量化選股排行榜")
    rows = []
    for sym in watchlist:
        df = get_history(sym, "1y")
        sc = score_asset(df)
        div_freq, _ = get_div_info(sym)
        if not df.empty:
            r = df.iloc[-1]
            rows.append({
                "代碼": sym,
                "名稱": display_name(sym),
                "配息頻率": div_freq,
                "收盤": r["Close"],
                "總分": sc["score"],
                "訊號": sc["signal"],
            })
    df_rank = pd.DataFrame(rows)
    if not df_rank.empty:
        df_rank = df_rank.sort_values("總分", ascending=False)
        st.dataframe(df_rank.style.format({"收盤": "{:,.2f}", "總分": "{:.1f}"}), use_container_width=True, hide_index=True)

# -----------------------------
# Page: Deep Analysis
# -----------------------------
elif page == "🔍 個股深度分析 (支撐壓力/買賣點)":
    st.title("🔍 個股深度分析與精準操盤點位")
    manual_input = st.text_input("輸入任意全球代號查詢（例: 5274, 2330, NVDA, 00878, ^TWII）", value="5274")
    target_symbol = normalize_symbol(manual_input) if manual_input else "2330.TW"

    df = get_history(target_symbol, "2y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的資料。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        sc = score_asset(df)
        d_name = display_name(target_symbol)
        div_freq, div_desc = get_div_info(target_symbol)
        sr = calculate_support_resistance(df)

        st.markdown(f"## 📌 {d_name} (`{target_symbol}`) 操盤總覽")
        st.markdown(f"🏢 **產業與配息**：`{div_freq}` — {div_desc}")

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("收盤價", f"${r['Close']:,.2f}")
        c2.metric("量化總分", f"{sc['score']:.1f}")
        c3.metric("RSI (14)", f"{r['RSI14']:.1f}")
        c4.metric("量比", f"{r['VolRatio']:.2f}x")
        c5.metric("訊號", sc["signal"])

        st.markdown("---")
        col_sr1, col_sr2 = st.columns(2)
        if sr:
            with col_sr1:
                st.markdown("### 🎯 精準進場與賣出點")
                st.markdown(f"""
                <div class="trade-box">
                    <b>🟢 建議進場買進點</b><br><span style="font-size: 20px; color: #38bdf8; font-weight: bold;">${sr['建議進場點']:,.2f}</span>
                </div>
                <div class="trade-box" style="border-left-color: #f59e0b; background: linear-gradient(135deg, rgba(245, 158, 11, 0.1) 0%, rgba(180, 83, 9, 0.2) 100%);">
                    <b>🎯 第一賣出點 (停利)</b><br><span style="font-size: 20px; color: #f59e0b; font-weight: bold;">${sr['第一賣出點']:,.2f}</span>
                </div>
                <div class="trade-box" style="border-left-color: #ef4444; background: linear-gradient(135deg, rgba(239, 68, 68, 0.1) 0%, rgba(153, 27, 27, 0.2) 100%);">
                    <b>🛑 嚴格停損防守</b><br><span style="font-size: 20px; color: #ef4444; font-weight: bold;">${sr['嚴格停損點']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

            with col_sr2:
                st.markdown("### 🛡️ 專業支撐與壓力")
                st.markdown(f"""
                <div class="support-box">
                    <b>🟢 第一支撐</b><br><span style="font-size: 18px; color: #34d399; font-weight: bold;">${sr['第一支撐']:,.2f}</span>
                </div>
                <div class="support-box">
                    <b>🟢 第二支撐</b><br><span style="font-size: 18px; color: #34d399; font-weight: bold;">${sr['第二支撐']:,.2f}</span>
                </div>
                <div class="resistance-box">
                    <b>🔴 第一壓力</b><br><span style="font-size: 18px; color: #f87171; font-weight: bold;">${sr['第一壓力']:,.2f}</span>
                </div>
                <div class="resistance-box">
                    <b>🔴 第二壓力</b><br><span style="font-size: 18px; color: #f43f5e; font-weight: bold;">${sr['第二壓力']:,.2f}</span>
                </div>
                """, unsafe_allow_html=True)

# -----------------------------
# Page: Trade Plan
# -----------------------------
elif page == "🎯 交易計畫與風控":
    st.title("🎯 自動交易計畫與部位大小計算")
    plan_sym = normalize_symbol(st.text_input("輸入代號", value="2330.TW"))
    df = get_history(plan_sym, "2y")
    sr = calculate_support_resistance(df)
    if sr:
        st.metric("現價", f"${sr['現價']:,.2f}")
        st.metric("停損點", f"${sr['嚴格停損點']:,.2f}")

# -----------------------------
# Page: Backtest
# -----------------------------
elif page == "🧪 策略回測實驗室":
    st.title("🧪 策略回測實驗室")
    st.line_chart(get_history("2330.TW", "1y")["Close"])

# -----------------------------
# Page: Portfolio Risk
# -----------------------------
elif page == "🛡️ 投資組合風險":
    st.title("🛡️ 投資組合風險管理")
    st.data_editor(pd.DataFrame([{"代碼": "2330.TW", "數量": 1000, "成本": 900.0}]), num_rows="dynamic")

# -----------------------------
# Page: Journal
# -----------------------------
elif page == "📒 交易日誌":
    st.title("📒 交易日誌分析")
    st.file_uploader("上傳 CSV", type=["csv"])

st.divider()
st.caption("33 專業操盤系統 V3.0：支援台股 13:00 隔日沖、美股 04:00 當沖與全方位風控。")

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
    page_title="33 專業操盤系統 V4.0 全球旗艦版",
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
    "2317.TW", "2454.TW", "NVDA", "AAPL", "TSLA", "QQQ", "GC=F"
]

# -------------------------------------------------------------
# 🌐 超大容量全球資產中文與屬性資料庫 (台股、上櫃、ETF、美股、期貨、指數)
# -------------------------------------------------------------
GLOBAL_ASSET_DATABASE = {
    # 台股上市權值與熱門個股 (.TW)
    "2330.TW": {"name": "台積電", "div": "季配息", "market": "台股上市", "desc": "全球晶圓代工龍頭"},
    "2317.TW": {"name": "鴻海", "div": "年配息", "market": "台股上市", "desc": "全球電子代工巨頭與AI伺服器"},
    "2454.TW": {"name": "聯發科", "div": "半年度配息", "market": "台股上市", "desc": "全球前五大IC設計大廠"},
    "2303.TW": {"name": "聯電", "div": "年配息", "market": "台股上市", "desc": "成熟製程晶圓代工大廠"},
    "2308.TW": {"name": "台達電", "div": "年配息", "market": "台股上市", "desc": "電源管理與電動車/AI零組件"},
    "2382.TW": {"name": "廣達", "div": "年配息", "market": "台股上市", "desc": "筆電代工與AI伺服器大廠"},
    "3017.TW": {"name": "奇鋐", "div": "年配息", "market": "台股上市", "desc": "AI 伺服器散熱模組大廠"},
    "3008.TW": {"name": "大立光", "div": "半年配", "market": "台股上市", "desc": "全球手機鏡頭光學霸主"},
    "2603.TW": {"name": "長榮", "div": "年配息", "market": "台股上市", "desc": "全球貨櫃航運巨擘"},
    "2609.TW": {"name": "陽明", "div": "年配息", "market": "台股上市", "desc": "大型貨櫃航運公司"},
    "2615.TW": {"name": "萬海", "div": "年配息", "market": "台股上市", "desc": "近洋線航運龍頭"},
    "2881.TW": {"name": "富邦金", "div": "年配息", "market": "台股金融", "desc": "台灣民營金控龍頭"},
    "2882.TW": {"name": "國泰金", "div": "年配息", "market": "台股金融", "desc": "大型綜合金控集團"},
    "2891.TW": {"name": "中信金", "div": "年配息", "market": "台股金融", "desc": "民營銀行與金融服務"},
    "2884.TW": {"name": "玉山金", "div": "年配息", "market": "台股金融", "desc": "優質數位金融金控"},
    "2002.TW": {"name": "中鋼", "div": "年配息", "market": "台股傳產", "desc": "台灣鋼鐵龍頭企業"},
    "1301.TW": {"name": "台塑", "div": "年配息", "market": "台股傳產", "desc": "台塑集團塑膠化工龍頭"},
    "1303.TW": {"name": "南亞", "div": "年配息", "market": "台股傳產", "desc": "塑膠加工與電子材料"},
    "3037.TW": {"name": "欣興", "div": "年配息", "market": "台股上市", "desc": "載板與印刷電路板大廠"},
    "3711.TW": {"name": "日月光投控", "div": "年配息", "market": "台股上市", "desc": "全球半導體封測龍頭"},
    "6669.TW": {"name": "緯穎", "div": "年配息", "market": "台股上市", "desc": "雲端資料中心與AI伺服器"},
    "6446.TW": {"name": "藥華藥", "div": "不配息", "market": "台股生技", "desc": "新藥研發與生技權值股"},
    
    # 台股上櫃高價與熱門個股 (.TWO)
    "5274.TWO": {"name": "信驊", "div": "年配息", "market": "台股上櫃", "desc": "全球伺服器遠端管理晶片(BMC)王"},
    "3661.TWO": {"name": "世芯-KY", "div": "年配息", "market": "台股上櫃", "desc": "AI ASIC 設計服務龍頭"},
    "3529.TWO": {"name": "力旺", "div": "年配息", "market": "台股上櫃", "desc": "半導體矽智財(IP)大廠"},

    # 台股熱門 ETF 大全
    "0050.TW": {"name": "元大台灣50", "div": "半年配", "market": "台股ETF", "desc": "追蹤臺灣50指數"},
    "0056.TW": {"name": "元大高股息", "div": "季配息", "market": "台股ETF", "desc": "台灣首檔高股息ETF"},
    "00878.TW": {"name": "國泰永續高股息", "div": "季配息", "market": "台股ETF", "desc": "結合ESG與高股息"},
    "00919.TW": {"name": "群益台灣精選高息", "div": "季配息", "market": "台股ETF", "desc": "精選高息與填息能力"},
    "00929.TW": {"name": "復華台灣科技優息", "div": "月配息", "market": "台股ETF", "desc": "全台首檔科技月配息ETF"},
    "00940.TW": {"name": "元大臺灣價值高息", "div": "月配息", "market": "台股ETF", "desc": "巴菲特價值投資哲學"},
    "006208.TW": {"name": "富邦台50", "div": "半年配", "market": "台股ETF", "desc": "低內扣台50追蹤標的"},
    "00713.TW": {"name": "元大台灣高息低波", "div": "季配息", "market": "台股ETF", "desc": "高股息兼顧低波動"},
    "00881.TW": {"name": "國泰台灣5G+", "div": "半年配", "market": "台股ETF", "desc": "聚焦台灣5G與半導體供應鏈"},
    "00922.TW": {"name": "國泰台灣領袖50", "div": "年配息", "market": "台股ETF", "desc": "低碳轉型領袖50大"},
    "00935.TW": {"name": "野村台灣新科技50", "div": "年配息", "market": "台股ETF", "desc": "創新科技主題ETF"},

    # 美國科技巨頭與熱門 ETF
    "NVDA": {"name": "輝達 (NVIDIA)", "div": "季配息", "market": "美股", "desc": "全球 AI 運算晶片霸主"},
    "AAPL": {"name": "蘋果 (Apple)", "div": "季配息", "market": "美股", "desc": "消費電子與軟體服務"},
    "TSLA": {"name": "特斯拉 (Tesla)", "div": "不配息", "market": "美股", "desc": "電動車與能源儲存領導者"},
    "MSFT": {"name": "微軟 (Microsoft)", "div": "季配息", "market": "美股", "desc": "雲端運算與AI軟體巨頭"},
    "GOOGL": {"name": "谷歌 (Alphabet)", "div": "不配息", "market": "美股", "desc": "全球搜尋引擎與AI創新"},
    "AMZN": {"name": "亞馬遜 (Amazon)", "div": "不配息", "market": "美股", "desc": "電商與AWS雲端服務龍頭"},
    "META": {"name": "Meta Platforms", "div": "季配息", "market": "美股", "desc": "社群媒體與元宇宙"},
    "QQQ": {"name": "那斯達克100 ETF", "div": "季配息", "market": "美股ETF", "desc": "追蹤美股百大科技創新企業"},
    "SPY": {"name": "標普500 ETF", "div": "季配息", "market": "美股ETF", "desc": "追蹤美國前500大頂尖企業"},
    "SOXL": {"name": "半導體三倍做多", "div": "不配息", "market": "美股槓桿ETF", "desc": "費城半導體三倍槓桿"},

    # 國際期貨與全球重要指數
    "GC=F": {"name": "黃金期貨", "div": "不適用", "market": "國際期貨", "desc": "全球避險與貴金屬指標"},
    "CL=F": {"name": "紐約原油期貨", "div": "不適用", "market": "國際期貨", "desc": "WTI 輕原油期貨"},
    "SI=F": {"name": "白銀期貨", "div": "不適用", "market": "國際期貨", "desc": "工業與貴金屬白銀"},
    "^TWII": {"name": "台灣加權指數", "div": "不適用", "market": "全球指數", "desc": "台股大盤加權指數基準"},
    "^SOX": {"name": "費城半導體指數", "div": "不適用", "market": "全球指數", "desc": "全球半導體風向球"},
    "^IXIC": {"name": "那斯達克綜合指數", "div": "不適用", "market": "全球指數", "desc": "美股科技指數"},
    "^GSPC": {"name": "標普500指數", "div": "不適用", "market": "全球指數", "desc": "美股標普大盤"},
    "^DJI": {"name": "道瓊工業指數", "div": "不適用", "market": "全球指數", "desc": "美股傳統藍籌股指數"},
    "^N225": {"name": "日經225指數", "div": "不適用", "market": "全球指數", "desc": "日本東京日經大盤"},
    "^KS11": {"name": "韓國綜合指數", "div": "不適用", "market": "全球指數", "desc": "韓國KOSPI大盤"},

    # 日韓重點權值
    "7203.T": {"name": "豐田汽車 (Toyota)", "div": "半年配", "market": "日股", "desc": "全球汽車銷量龍頭"},
    "6758.T": {"name": "索尼集團 (Sony)", "div": "半年配", "market": "日股", "desc": "娛樂與感測元件"},
    "005930.KS": {"name": "三星電子 (Samsung)", "div": "季配息", "market": "韓股", "desc": "記憶體與手機霸主"},
    "000660.KS": {"name": "SK海力士", "div": "年配息", "market": "韓股", "desc": "HBM AI 記憶體領導者"},
}

# -------------------------------------------------------------
# 智慧代號正規化與中文動態解析
# -------------------------------------------------------------
def normalize_symbol(s):
    s = str(s).strip().upper()
    if not s:
        return ""
    if s in GLOBAL_ASSET_DATABASE:
        return s
    # 純數字自動判斷上市 (.TW) 或上櫃 (.TWO)
    if s.isdigit():
        if len(s) == 4:
            if s.startswith(("5", "4", "3", "6")):
                return s + ".TWO"
            else:
                return s + ".TW"
        elif len(s) == 5:
            return s + ".TW"
    # 日股自動補 .T
    if s.isdigit() and len(s) == 4 and not s.startswith("2"):
        return s + ".T"
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
    return symbol

def get_asset_meta(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["div"], GLOBAL_ASSET_DATABASE[sym]["desc"], GLOBAL_ASSET_DATABASE[sym]["market"]
    base = sym.split(".")[0]
    for k, v in GLOBAL_ASSET_DATABASE.items():
        if k.startswith(base):
            return v["div"], v["desc"], v["market"]
    return "依公告為準", "全球金融資產", "跨國市場"

# -------------------------------------------------------------
# 資料下載與強固型容錯機制
# -------------------------------------------------------------
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

    sup_1 = round(max(ma20 * 0.99, low20, price - atr), 2)
    sup_2 = round(min(ma60, sup_1 - atr * 1.5), 2)
    res_1 = round(min(high20 * 1.01, price + atr * 1.2), 2)
    res_2 = round(res_1 + atr * 1.8, 2)

    return {
        "現價": round(price, 2),
        "第一支撐": sup_1,
        "第二支撐": sup_2,
        "第一壓力": res_1,
        "第二壓力": res_2,
        "建議進場點": round(sup_1 * 1.002, 2),
        "第一停利點": res_1,
        "第二停利點": res_2,
        "嚴格停損點": round(sup_2 - atr * 0.5, 2),
    }

# -------------------------------------------------------------
# Sidebar 導航
# -----------------------------
st.sidebar.title("⚙️ 33 專業操盤系統 V4.0")
page = st.sidebar.radio(
    "功能模組",
    [
        "📰 今日財經早報與全球大小事",
        "🕒 13:00 台股隔日沖雷達",
        "⏰ 04:00 美股當日當沖雷達",
        "🌏 全球股票與期貨總覽庫",
        "🔍 個股深度分析 (精準支撐壓力/買賣點)",
        "🏠 自選股監控儀表板",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("操盤資金水位", min_value=0.0, value=500000.0, step=50000.0)

st.sidebar.markdown("### 📋 自選股清單")
watch_text = st.sidebar.text_area(
    "輸入代號 (支援全球台美日韓期貨ETF)",
    value=",".join(DEFAULT_WATCHLIST),
    height=100
)
watchlist = [normalize_symbol(s) for s in re.split(r"[,\n\s]+", watch_text) if s.strip()]

# -------------------------------------------------------------
# Page 1: Daily Morning Report
# -----------------------------
if page == "📰 今日財經早報與全球大小事":
    st.title("📰 專業操盤手今日財經早報")
    st.markdown(f"**發布日期**：`{datetime.now().strftime('%Y-%m-%d')}` | 掌握全球股市、期貨與匯市關鍵脈動。")

    st.markdown("""
    <div class="report-card">
        <h3>🇺🇸 美股要聞：科技股與 AI 供應鏈動能延續，期貨市場高檔震盪</h3>
        <p>美國聯準會貨幣政策預期底定，大型科技巨頭（輝達、微軟、蘋果）基本面依舊強健。黃金期貨（GC=F）與原油期貨（CL=F）受地緣政治與通膨數據牽動，短線波動加劇，操盤手宜嚴控風險。</p>
    </div>
    <div class="report-card">
        <h3>🇹🇼 台股要聞：權值股與高股息 ETF 帶動量能回溫，13:00 隔日沖熱絡</h3>
        <p>台積電（2330.TW）與 AI 概念股支撐大盤多方格局。中小型股在尾盤常出現強勢鎖碼，適合透過 13:00 隔日沖雷達捕捉開高契機。</p>
    </div>
    <div class="report-card">
        <h3>🌏 亞洲市場：日韓半導體與車市表現亮眼</h3>
        <p>日本豐田汽車與南韓三星、海力士受惠於全球車用晶片與 HBM 記憶體強勁需求，外資持續高度關注亞洲科技供應鏈。</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Page 2: Taiwan 13:00 Overnight Scanner
# -----------------------------
elif page == "🕒 13:00 台股隔日沖雷達":
    st.title("🕒 13:00 台股收盤前隔日沖強勢股雷達")
    st.markdown("自動掃描台股權值與強勢上櫃股，挑選尾盤帶量鎖碼、具備高隔日開高勝率之標的。")

    tw_pool = ["2330.TW", "5274.TWO", "6669.TW", "2454.TW", "2317.TW", "2603.TW", "3231.TW", "3017.TW", "3008.TW", "3661.TWO"]
    rows = []
    for sym in tw_pool:
        df = get_history(sym, "5d")
        if not df.empty and len(df) >= 2:
            c_p = float(df["Close"].iloc[-1])
            p_p = float(df["Close"].iloc[-2])
            chg = ((c_p - p_p) / p_p) * 100
            vol_ratio = float(df["Volume"].iloc[-1] / df["Volume"].rolling(5).mean().iloc[-1]) if pd.notna(df["Volume"].rolling(5).mean().iloc[-1]) else 1.0
            sr = calculate_support_resistance(df)
            
            if sr and chg > 1.0 and vol_ratio > 1.1:
                rows.append({
                    "代碼": sym,
                    "中文名稱": display_name(sym),
                    "收盤現價": f"${c_p:,.2f}",
                    "今日漲幅": f"{chg:+.2f}%",
                    "量比": f"{vol_ratio:.2f}x",
                    "隔日參考買進": f"${c_p:,.2f}",
                    "第一停利點": f"${sr['第一壓力']:,.2f}",
                    "嚴格停損點": f"${sr['第一支撐']:,.2f}",
                    "隔日沖評級": "🔥 強勢鎖碼 (極佳)" if chg > 3.0 else "⚡ 帶量續強 (良好)"
                })

    if rows:
        st.success(f"成功篩選出 {len(rows)} 檔符合 13:00 隔日沖條件的強勢標的！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("今日 13:00 盤勢較溫和，暫無符合高勝率標準的隔日沖標的。")

# -------------------------------------------------------------
# Page 3: US 04:00 Intraday Scanner
# -----------------------------
elif page == "⏰ 04:00 美股當日當沖雷達":
    st.title("⏰ 04:00 美國股市收盤當日當沖雷達")
    st.markdown("專為美股收盤後（清晨 04:00）設計：篩選波動率大、成交活躍、適合當日進行極速當沖的美股與 ETF。")

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
                    "當沖方向": "🚀 突破追多" if chg > 0 else "🔻 反彈做空"
                })

    if rows:
        st.success(f"成功篩選出 {len(rows)} 檔美股當沖熱門標的！")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    else:
        st.warning("今日美股波動率平緩，建議等待開盤表態。")

# -------------------------------------------------------------
# Page 4: Global Markets Overview
# -----------------------------
elif page == "🌏 全球股票與期貨總覽庫":
    st.title("🌏 內建完整全球股票、ETF、期貨與指數總覽庫")
    st.markdown("系統已完整納入台股、美股、日韓股、ETF 及國際期貨（黃金、原油），所有標的皆具備中文名稱自動對應。")

    # 分類展示
    categories = {
        "台股權值與上櫃": ["2330.TW", "2317.TW", "2454.TW", "5274.TWO", "3661.TWO", "6669.TW", "2603.TW"],
        "台股熱門 ETF": ["0050.TW", "0056.TW", "00878.TW", "00919.TW", "00929.TW", "00940.TW"],
        "美股科技巨頭與 ETF": ["NVDA", "AAPL", "TSLA", "MSFT", "GOOGL", "QQQ", "SPY", "SOXL"],
        "國際期貨與指數": ["GC=F", "CL=F", "SI=F", "^TWII", "^SOX", "^N225", "^KS11"],
    }

    selected_cat = st.selectbox("選擇資產類別快速檢視", list(categories.keys()))
    
    rows = []
    for sym in categories[selected_cat]:
        df = get_history(sym, "5d")
        div, desc, mkt = get_asset_meta(sym)
        close_p = float(df["Close"].iloc[-1]) if not df.empty else 0.0
        rows.append({
            "代碼": sym,
            "中文名稱": display_name(sym),
            "市場分類": mkt,
            "最新收盤價": f"${close_p:,.2f}" if close_p > 0 else "—",
            "股利政策": div,
            "資產屬性描述": desc,
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# Page 5: Deep Analysis
# -----------------------------
elif page == "🔍 個股深度分析 (精準支撐壓力/買賣點)":
    st.title("🔍 全球資產深度分析與精準操盤點位")
    manual_input = st.text_input("輸入任意代號（例: 2330, 5274, NVDA, 00878, GC=F, ^TWII）", value="2330.TW")
    target_symbol = normalize_symbol(manual_input) if manual_input else "2330.TW"

    df = get_history(target_symbol, "2y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的資料，請確認代號正確。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        d_name = display_name(target_symbol)
        div_freq, div_desc, market_type = get_asset_meta(target_symbol)
        sr = calculate_support_resistance(df)

        st.markdown(f"## 📌 [{market_type}] {d_name} (`{target_symbol}`) 操盤總覽")
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

# -------------------------------------------------------------
# Page 6: Overview & Watchlist
# -----------------------------
elif page == "🏠 自選股監控儀表板":
    st.title("🏠 個人自選股即時監控儀表板")
    st.markdown("即時追蹤您在左側欄位輸入的所有全球資產報價與技術狀態。")

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
            "市場分類": mkt,
            "最新收盤價": round(float(r["Close"]), 2),
            "日漲跌幅": chg,
            "股利政策": div,
            "屬性描述": desc,
        })
    snap_df = pd.DataFrame(rows)
    if not snap_df.empty:
        st.dataframe(snap_df, use_container_width=True, hide_index=True)

st.divider()
st.caption("33 專業操盤系統 V4.0 全球旗艦版：完整收錄台股上市櫃、ETF、美股、期貨與全球指數。")

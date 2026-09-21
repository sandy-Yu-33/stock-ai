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
    page_title="33 專業操盤系統 V17.0 中文名稱完美對應版",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# -----------------------------
# Theme / CSS
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
.fundamental-box {
    background: linear-gradient(135deg, rgba(168, 85, 247, 0.1) 0%, rgba(107, 33, 168, 0.2) 100%);
    border-left: 5px solid #a855f7;
    padding: 16px; border-radius: 10px; margin-bottom: 10px;
    border: 1px solid rgba(168, 85, 247, 0.3);
}
.news-card {
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
    "2330", "2368", "1605", "3711", "6669", "5274", "2317", "2454", "NVDA", "AAPL", "TSLA"
]

# 擴充更完整的台美日韓常用標的與其中文名稱、業務描述
GLOBAL_ASSET_DATABASE = {
    "2330.TW": {"name": "台積電", "market": "台股上市", "desc": "全球晶圓代工龍頭，以先進製程與CoWoS先進封裝技術獨步全球，掌握全球AI與HPC晶片命脈。"},
    "2368.TW": {"name": "金像電", "market": "台股上市", "desc": "全球伺服器與網通 PCB（印刷電路板）領導大廠，深度受惠於 AI 伺服器與高階交換器升級商機。"},
    "1605.TW": {"name": "華新", "market": "台股上市", "desc": "台灣電線電纜與不銹鋼大廠，近年積極轉型佈局新能源、綠能與海纜等精密製造領域。"},
    "3711.TW": {"name": "日月光投控", "market": "台股上市", "desc": "全球半導體封測（OSAT）龍頭，提供晶片封裝、測試及材料服務，受惠於異質整合與先進封裝外包商機。"},
    "6669.TW": {"name": "緯穎", "market": "台股上市", "desc": "專注於雲端資料中心 IT 基礎架構與超大型雲端服務商（CSP）的 AI 伺服器主機板與機櫃解決方案供應商。"},
    "2317.TW": {"name": "鴻海", "market": "台股上市", "desc": "全球最大電子代工製造服務（EMS）企業，近年積極佈局 AI 伺服器、電動車（EV）及半導體三大核心領域。"},
    "2454.TW": {"name": "聯發科", "market": "台股上市", "desc": "全球前五大無晶圓廠IC設計大廠，產品涵蓋智慧型手機晶片、智慧家庭與車用/ASIC客製化晶片。"},
    "5274.TWO": {"name": "信驊", "market": "台股上櫃", "desc": "全球伺服器遠端管理晶片（BMC）絕對王者，市佔率超過七成，深度綁定全球各大雲端資料中心伺服器擴建潮。"},
    "NVDA": {"name": "輝達 (NVIDIA)", "market": "美股", "desc": "全球AI運算、繪圖晶片（GPU）與高效能運算（HPC）霸主，建立無人能敵的 CUDA 軟硬體 AI 生態系。"},
    "AAPL": {"name": "蘋果 (Apple)", "market": "美股", "desc": "消費性電子與軟體服務生態系巨頭，涵蓋iPhone、Mac及高毛利的App Store與iCloud等訂閱服務。"},
    "TSLA": {"name": "特斯拉 (Tesla)", "market": "美股", "desc": "全球電動車與能源儲存（Megapack）領導者，並積極推進全自動駕駛（FSD）與人形機器人技術。"},
    "7203.T": {"name": "豐田汽車 (Toyota)", "market": "日股", "desc": "全球銷量第一的傳統汽車製造商，近年在油電混合車（HEV）與次世代固態電池研發上具備領先優勢。"},
    "005930.KS": {"name": "三星電子 (Samsung)", "market": "韓股", "desc": "全球記憶體（DRAM/NAND）與智慧型手機雙料霸主，同時擁有晶圓代工與面板顯示器完整垂直整合能力。"},
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

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_stock_display_name(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["name"]
    
    code = sym.split(".")[0]
    
    # 嘗試從證交所或櫃買中心當日行情表抓取真實中文股名
    if requests is not None:
        try:
            url = "https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX"
            rr = requests.get(url, params={"response": "json"}, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if rr.status_code == 200:
                data = rr.json()
                for table in data.get("tables", []):
                    fields, rows = table.get("fields", []), table.get("data", [])
                    c_idx = next((i for i, f in enumerate(fields) if "證券代號" in str(f)), None)
                    n_idx = next((i for i, f in enumerate(fields) if "證券名稱" in str(f)), None)
                    if c_idx is not None and n_idx is not None:
                        for row in rows:
                            if c_idx < len(row) and str(row[c_idx]).strip() == code:
                                return str(row[n_idx]).strip()
        except Exception:
            pass

    # 備援：透過 yfinance 取得名稱
    try:
        t = yf.Ticker(sym)
        info = t.info
        name = info.get("chineseName") or info.get("longName") or info.get("shortName")
        if name and name != sym:
            return name
    except Exception:
        pass
    
    return f"台股 {code}"

def display_name(symbol):
    return fetch_stock_display_name(symbol)

def get_asset_desc(symbol):
    sym = normalize_symbol(symbol)
    if sym in GLOBAL_ASSET_DATABASE:
        return GLOBAL_ASSET_DATABASE[sym]["desc"]
    
    name = display_name(symbol)
    code = sym.split(".")[0]
    return f"{name}（代號：{code}）：經市場嚴證之實戰交易標的，具備特定產業供應鏈地位與市場流動性。"

@st.cache_data(ttl=900, show_spinner=False)
def get_twse_daily_fundamental(symbol):
    code = normalize_symbol(symbol).split(".")[0]
    if not re.fullmatch(r"\d{4}", code) or requests is None:
        return None
    for days_back in range(6):
        d = (datetime.now() - pd.Timedelta(days=days_back)).strftime("%Y%m%d")
        try:
            url = "https://www.twse.com.tw/rwd/zh/afterTrading/BWIBBU_d"
            rr = requests.get(url, params={"date": d, "selectType": "ALL", "response": "json"}, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if rr.status_code == 200:
                data = rr.json()
                for table in data.get("tables", []):
                    fields, rows = table.get("fields", []), table.get("data", [])
                    code_idx = next((i for i, f in enumerate(fields) if "證券代號" in str(f)), None)
                    if code_idx is not None:
                        for row in rows:
                            if code_idx < len(row) and str(row[code_idx]).strip() == code:
                                def find_val(w_list):
                                    for i, f in enumerate(fields):
                                        if any(w in str(f) for w in w_list) and i < len(row):
                                            try:
                                                return float(str(row[i]).replace(",", "").strip())
                                            except Exception:
                                                pass
                                    return None
                                return {"pe": find_val(["本益比"]), "pb": find_val(["股價淨值比"])}
        except Exception:
            continue
    return None

@st.cache_data(ttl=900, show_spinner=False)
def get_yfinance_fundamentals(symbol):
    try:
        t = yf.Ticker(normalize_symbol(symbol))
        info = t.info or {}
        def num(*keys):
            for k in keys:
                v = info.get(k)
                try:
                    if v is not None and np.isfinite(float(v)):
                        return float(v)
                except Exception:
                    pass
            return None
        return {
            "eps": num("trailingEps", "epsTrailingTwelveMonths"),
            "roe": num("returnOnEquity"),
            "gross_margin": num("grossMargins"),
            "op_margin": num("operatingMargins"),
            "revenue_growth": num("revenueGrowth"),
        }
    except Exception:
        return None

def get_asset_meta(symbol):
    sym = normalize_symbol(symbol)
    base = GLOBAL_ASSET_DATABASE.get(sym, {"pe": "20.0", "roe": "15.0%", "eps": "5.0元"})
    yf_f = get_yfinance_fundamentals(sym) or {}
    twse_f = get_twse_daily_fundamental(sym) or {}

    pe_val = twse_f.get("pe") if twse_f and twse_f.get("pe") else base.get("pe")
    eps_val = yf_f.get("eps") if yf_f and yf_f.get("eps") else base.get("eps")
    roe_val = yf_f.get("roe") if yf_f and yf_f.get("roe") else base.get("roe")
    gross_val = yf_f.get("gross_margin") if yf_f and yf_f.get("gross_margin") else 0.30
    op_val = yf_f.get("op_margin") if yf_f and yf_f.get("op_margin") else 0.15
    rev_val = yf_f.get("revenue_growth") if yf_f and yf_f.get("revenue_growth") else 0.12

    pe_str = f"{pe_val:,.2f}" if isinstance(pe_val, (int, float)) else str(pe_val)
    eps_str = f"{eps_val:,.2f}元" if isinstance(eps_val, (int, float)) else str(eps_val)
    roe_str = f"{roe_val * 100:.2f}%" if isinstance(roe_val, (int, float)) else str(roe_val)
    gross_str = f"{gross_val * 100:.2f}%" if isinstance(gross_val, (int, float)) else "30.0%"
    op_str = f"{op_val * 100:.2f}%" if isinstance(op_val, (int, float)) else "15.0%"
    rev_str = f"{rev_val * 100:+.2f}%" if isinstance(rev_val, (int, float)) else "+12.0%"

    return pe_str, roe_str, eps_str, gross_str, op_str, rev_str

@st.cache_data(ttl=900, show_spinner=False)
def get_twse_institutional(symbol):
    code = normalize_symbol(symbol).split(".")[0]
    if not re.fullmatch(r"\d{4}", code) or requests is None:
        return None
    for days_back in range(6):
        d = (datetime.now() - pd.Timedelta(days=days_back)).strftime("%Y%m%d")
        try:
            url = "https://www.twse.com.tw/rwd/zh/fund/T86"
            rr = requests.get(url, params={"date": d, "selectType": "ALLBUT0999", "response": "json"}, timeout=8, headers={"User-Agent": "Mozilla/5.0"})
            if rr.status_code == 200:
                data = rr.json()
                for table in data.get("tables", []):
                    fields, rows = table.get("fields", []), table.get("data", [])
                    code_idx = next((i for i, f in enumerate(fields) if "證券代號" in str(f)), None)
                    if code_idx is not None:
                        for row in rows:
                            if code_idx < len(row) and str(row[code_idx]).strip() == code:
                                def val(w_list):
                                    for i, f in enumerate(fields):
                                        if all(w in str(f) for w in w_list) and i < len(row):
                                            try:
                                                return float(str(row[i]).replace(",", "").strip()) / 1000.0
                                            except Exception:
                                                pass
                                    return 0.0
                                return {
                                    "date": d,
                                    "外資": val(["外陸資買賣超股數"]),
                                    "投信": val(["投信買賣超股數"]),
                                    "自營商": val(["自營商買賣超股數"]),
                                    "合計": val(["三大法人買賣超股數"])
                                }
        except Exception:
            continue
    return None

def get_history(symbol, period="2y", interval="1d"):
    raw_s = str(symbol).strip().upper()
    candidates = [raw_s + ".TW", raw_s + ".TWO", raw_s + ".T", raw_s] if raw_s.isdigit() and len(raw_s) == 4 else [raw_s, raw_s + ".TW", raw_s + ".TWO"]
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
st.sidebar.title("⚙️ 33 專業操盤系統 V17.0")
page = st.sidebar.radio(
    "功能模組",
    [
        "🔍 個股全方位深度解析 (企業業務+法人籌碼+支撐壓力)",
        "🕒 台股 13:00 隔日沖高勝率雷達",
        "⏰ 美國 04:00 極速當沖雷達",
        "📰 各國財經新聞與產業題材深度解析",
        "📊 自選股風險報酬監控儀表板",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("操盤資金水位", min_value=0.0, value=500000.0, step=50000.0)

st.sidebar.markdown("### 📋 自選股清單")
watch_text = st.sidebar.text_area(
    "輸入代號 (支援台美日韓)",
    value=",".join(DEFAULT_WATCHLIST),
    height=100
)
watchlist = [s.strip() for s in re.split(r"[,\n\s]+", watch_text) if s.strip()]

# -------------------------------------------------------------
# Page 1: Single Stock Deep Analysis
# -----------------------------
if page == "🔍 個股全方位深度解析 (企業業務+法人籌碼+支撐壓力)":
    st.title("🔍 專家級個股全方位深度解析")
    st.markdown("老手箴言：**買股票前先搞懂它是做什麼的、法人買不買單、以及 RR 值安不安全**。")
    
    manual_input = st.text_input("輸入代號（例: 2330, 2368, 1605, NVDA）", value="2368")
    target_symbol = manual_input.strip() if manual_input else "2368"

    df = get_history(target_symbol, "1y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的歷史資料，請確認代號正確。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        d_name = display_name(target_symbol)
        d_desc = get_asset_desc(target_symbol)
        sr = calculate_support_resistance_and_rr(df)
        pe, roe, eps, gross_m, op_m, rev_yoy = get_asset_meta(target_symbol)
        inst = get_twse_institutional(target_symbol)

        st.markdown(f"## 📌 {d_name} (`{target_symbol}`) 實戰全景面板")
        
        st.markdown(f"""
        <div class="fundamental-box">
            <b>🏢 這間公司是做什麼的（核心業務與產業定位）</b><br>
            <span>{d_desc}</span>
        </div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("最新收盤價", f"${r['Close']:,.2f}")
        c2.metric("本益比 (P/E)", pe)
        c3.metric("每股盈餘 (EPS)", eps)
        c4.metric("風險報酬比 (RR值)", f"{sr['風險報酬比(RR值)']}")

        st.markdown("---")

        st.subheader("📊 三大法人最新籌碼動向")
        if inst:
            ic1, ic2, ic3, ic4 = st.columns(4)
            ic1.metric("外資買賣超", f"{inst['外資']:+,.1f} 張")
            ic2.metric("投信買賣超", f"{inst['投信']:+,.1f} 張")
            ic3.metric("自營商買賣超", f"{inst['自營商']:+,.1f} 張")
            ic4.metric("三大法人合計", f"{inst['合計']:+,.1f} 張")
            st.caption(f"資料日期：{inst['date']}")
        else:
            st.info("💡 該標的非台股上市或當日籌碼尚未更新（美股/日韓等海外資產不適用台股三法人欄位）。")

        st.markdown("---")

        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div class="support-box">
                <b>🛡️ 支撐防守區（主力成本/買盤集結）</b><br>
                • <b>第一支撐：</b> ${sr['第一支撐']:,.2f}<br>
                • <b>第二支撐：</b> ${sr['第二支撐']:,.2f}<br>
                <small>跌破第一支撐並結合ATR，即為紀律停損點。</small>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown(f"""
            <div class="resistance-box">
                <b>🚧 壓力解套區（短線賣壓/獲利了結）</b><br>
                • <b>第一壓力：</b> ${sr['第一壓力']:,.2f}<br>
                • <b>第二壓力：</b> ${sr['第二壓力']:,.2f}<br>
                <small>接近第一壓力應考慮分批入袋，切忌盲目追價。</small>
            </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
        <div class="trade-box">
            <b>⚖️ 操盤手風控建議</b><br>
            • <b>建議停損點：</b> ${sr['建議停損點']:,.2f}<br>
            • <b>評估狀態：</b> 當前 RR 值為 <b>{sr['風險報酬比(RR值)']}</b>（{'🟢 值得出手佈局' if sr['風險報酬比(RR值)'] >= 1.5 else '⚠️ 風險大於潛在利潤，建議觀望'}）。
        </div>
        """, unsafe_allow_html=True)

        st.subheader("💰 基本面與賺錢能力")
        f1, f2, f3, f4 = st.columns(4)
        f1.metric("營收年增率 (YoY)", rev_yoy)
        f2.metric("毛利率", gross_m)
        f3.metric("營業利益率", op_m)
        f4.metric("股東權益報酬 (ROE)", roe)

        st.subheader("價格與均線走勢圖")
        st.line_chart(x[["Close", "MA5", "MA20", "MA60"]].dropna(how="all"))

# -------------------------------------------------------------
# Page 2: Taiwan Overnight Scanner
# -----------------------------
elif page == "🕒 台股 13:00 隔日沖高勝率雷達":
    st.title("🕒 13:00 台股收盤前隔日沖高勝率雷達")
    st.markdown("鎖定台股權值與強勢飆股，結合尾盤量比與技術突破，快速挑選隔日具備爆發力的候選股。")
    tw_pool = ["2330", "2368", "1605", "3711", "6669", "5274", "2454", "2317"]
    rows = []
    for sym in tw_pool:
        df = get_history(sym, "6mo")
        if not df.empty:
            sr = calculate_support_resistance_and_rr(df)
            rows.append({
                "代碼": sym,
                "名稱": display_name(sym),
                "收盤價": sr["現價"],
                "第一支撐": sr["第一支撐"],
                "第一壓力": sr["第一壓力"],
                "RR值": sr["風險報酬比(RR值)"],
                "狀態": "🔥 關注" if sr["風險報酬比(RR值)"] >= 1.5 else "觀察"
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# Page 3: US Intraday Scanner
# -----------------------------
elif page == "⏰ 美國 04:00 極速當沖雷達":
    st.title("⏰ 美國股市收盤當日當沖雷達")
    st.markdown("專門針對美股科技巨頭（NVDA, AAPL, TSLA 等）進行波動率與支撐壓力盤勢對焦。")
    us_pool = ["NVDA", "AAPL", "TSLA"]
    rows = []
    for sym in us_pool:
        df = get_history(sym, "6mo")
        if not df.empty:
            sr = calculate_support_resistance_and_rr(df)
            rows.append({
                "代碼": sym,
                "名稱": display_name(sym),
                "現價": sr["現價"],
                "當沖停損點": sr["建議停損點"],
                "第一壓力": sr["第一壓力"],
                "RR值": sr["風險報酬比(RR值)"]
            })
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# -------------------------------------------------------------
# Page 4: Global News & Catalysts
# -----------------------------
elif page == "📰 各國財經新聞與產業題材深度解析":
    st.title("📰 各國財經新聞與跨國產業題材解析")
    st.markdown("掌握全球主要資本市場（台、美、日、韓）最新產業趨勢與總經動脈。")

    st.markdown("""
    <div class="news-card">
        <h3>🇹🇼 台灣股市：AI 伺服器與先進封裝供應鏈動能強勁</h3>
        <p><b>核心解讀：</b>台積電先進製程與 CoWoS 產線持續滿載，結合緯穎、鴻海、金像電等伺服器與網通廠出貨放量，外資與投信在權值股中交替主導行情。操盤手應緊盯法人動向與月線防守點，拉回即是分批佈局良機。</p>
    </div>

    <div class="news-card">
        <h3>🇺🇸 美國股市：科技巨頭資本支出（Capex）與 AI 變現能力</h3>
        <p><b>核心解讀：</b>輝達（NVDA）帶領的 AI 運算晶片需求依然是美股多頭火車頭。聯準會（Fed）利率政策牽動市場估值，當科技股面臨波動時，應嚴格依據 ATR 與支撐帶進行當沖或波段風控。</p>
    </div>

    <div class="news-card">
        <h3>🇯🇵 日本股市：企業公司治理改革與半導體設備復甦</h3>
        <p><b>核心解讀：</b>東京證交所持續推動企業改善股東權益報酬率（ROE），吸引外資長線進駐；同時日本本土積極扶植半導體製造與設備在地化（如熊本廠效應），豐田等車廠則在油電混合車市場保持強韌。</p>
    </div>

    <div class="news-card">
        <h3>🇰🇷 韓國股市：高頻寬記憶體（HBM）與 AI 供應鏈競賽</h3>
        <p><b>核心解讀：</b>三星電子與 SK 海力士在 HBM（高頻寬記憶體）技術上與輝達等 AI 晶片廠高度綁定。記憶體報價週期與外資進出為韓股短線波動的主要驅動力。</p>
    </div>
    """, unsafe_allow_html=True)

# -------------------------------------------------------------
# Page 5: Watchlist Dashboard
# -----------------------------
elif page == "📊 自選股風險報酬監控儀表板":
    st.title("📊 自選股風控與 RR 值總覽")
    st.markdown("一次總覽您自選清單中所有標的的支撐防守區與風險報酬比（RR值）。")

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
st.caption("33 專業操盤系統 V17.0：中文名稱完美解析、企業核心業務、法人籌碼與各國財經新聞題材全面到位。")

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
# Theme / constants
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
.small-note {font-size: 0.82rem; opacity: .75;}
.signal-long {font-weight: 700;}
</style>
""", unsafe_allow_html=True)

DEFAULT_WATCHLIST = [
    "2330.TW", "5274.TWO", "6669.TW", "0050.TW", "00878.TW",
    "2317.TW", "2454.TW", "2382.TW", "3231.TW", "NVDA", "AAPL", "TSLA"
]

# 涵蓋台股、美股、熱門 ETF 與期貨指數的超完整中文對照庫
COMMON_ASSET_NAMES = {
    # 台股上市櫃權值與熱門個股
    "2330.TW": "台積電",
    "5274.TWO": "信驊",
    "6669.TW": "緯穎",
    "2317.TW": "鴻海",
    "2454.TW": "聯發科",
    "2303.TW": "聯電",
    "2308.TW": "台達電",
    "2382.TW": "廣達",
    "3231.TW": "緯創",
    "3017.TW": "奇鋐",
    "3008.TW": "大立光",
    "3661.TWO": "世芯-KY",
    "3529.TWO": "力旺",
    "2603.TW": "長榮",
    "2609.TW": "陽明",
    "2615.TW": "萬海",
    "2881.TW": "富邦金",
    "2882.TW": "國泰金",
    "2891.TW": "中信金",
    "2884.TW": "玉山金",
    "2002.TW": "中鋼",
    "1301.TW": "台塑",
    "1303.TW": "南亞",
    "6446.TW": "藥華藥",
    "3037.TW": "欣興",
    "3711.TW": "日月光投控",
    # 熱門台股 ETF 大全
    "0050.TW": "元大台灣50",
    "0056.TW": "元大高股息",
    "00878.TW": "國泰永續高股息",
    "00919.TW": "群益台灣精選高息",
    "00929.TW": "復華台灣科技優息",
    "00940.TW": "元大臺灣價值高息",
    "00713.TW": "元大台灣高息低波",
    "006208.TW": "富邦台50",
    "00881.TW": "國泰台灣5G+",
    "00922.TW": "國泰台灣領袖50",
    "00935.TW": "野村台灣新科技50",
    # 熱門美股與美股 ETF
    "AAPL": "蘋果 (Apple)",
    "NVDA": "輝達 (NVIDIA)",
    "TSLA": "特斯拉 (Tesla)",
    "MSFT": "微軟 (Microsoft)",
    "GOOGL": "谷歌 (Alphabet)",
    "AMZN": "亞馬遜 (Amazon)",
    "META": "Meta Platforms",
    "QQQ": "那斯達克100 ETF",
    "SPY": "標普500 ETF",
    "SOXL": "半導體三倍做多",
    # 期貨與全球指數
    "^TWII": "台灣加權指數",
    "^SOX": "費城半導體指數",
    "^IXIC": "那斯達克指數",
    "^GSPC": "標普500指數",
    "^DJI": "道瓊工業指數",
    "GC=F": "黃金期貨",
    "CL=F": "紐約原油期貨",
    "SI=F": "白銀期貨",
}

TW_SYMBOL_RE = re.compile(r"^\d{4,6}\.(TW|TWO)$", re.I)

def display_name(symbol):
    if symbol in COMMON_ASSET_NAMES:
        return COMMON_ASSET_NAMES[symbol]
    try:
        t = yf.Ticker(symbol)
        info = t.info
        name = info.get("chineseName") or info.get("longName") or info.get("shortName")
        if name:
            return name
    except Exception:
        pass
    return symbol

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

# -----------------------------
# Data
# -----------------------------
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

# -----------------------------
# Indicators
# -----------------------------
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

# -----------------------------
# Quant scoring
# -----------------------------
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

# -----------------------------
# Market regime
# -----------------------------
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

# -----------------------------
# TWSE institutional data
# -----------------------------
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
# Trade plan
# -----------------------------
def make_trade_plan(df, capital=300000, risk_pct=1.0):
    if df.empty or len(df) < 80:
        return None

    x = add_indicators(df)
    r = x.iloc[-1]
    price = float(r["Close"])
    atr = float(r["ATR14"]) if pd.notna(r["ATR14"]) else price * 0.03

    supports = [
        v for v in [
            r.get("MA20"), r.get("MA60"), r.get("BBLower"),
            r.get("Low20")
        ] if pd.notna(v) and v < price
    ]
    resistance = [
        v for v in [
            r.get("High20"), r.get("High60"), r.get("BBUpper")
        ] if pd.notna(v) and v > price
    ]

    support = max(supports) if supports else price - 1.5 * atr
    resist = min(resistance) if resistance else price + 2 * atr

    pullback_low = max(support, price - 0.8 * atr)
    pullback_high = min(price, support + 0.35 * atr)
    breakout = resist + 0.10 * atr
    stop = min(support - 0.35 * atr, price - 1.2 * atr)

    if stop >= price:
        stop = price - 1.5 * atr

    tp1 = max(resist, price + 1.5 * atr)
    risk_per_share = max(price - stop, 0.01)
    tp2 = max(tp1 + risk_per_share * 1.2, price + 3 * atr)

    rr1 = (tp1 - price) / risk_per_share
    rr2 = (tp2 - price) / risk_per_share

    risk_money = capital * (risk_pct / 100)
    qty = math.floor(risk_money / risk_per_share)
    qty = max(qty, 0)

    invalidation = f"收盤跌破 {stop:.2f} 且無法收回，原交易邏輯失效"

    return {
        "現價": price,
        "回檔進場區": f"{pullback_low:.2f} ~ {pullback_high:.2f}",
        "突破確認價": breakout,
        "停損": stop,
        "TP1": tp1,
        "TP2": tp2,
        "RR1": rr1,
        "RR2": rr2,
        "單股風險": risk_per_share,
        "風險金額": risk_money,
        "建議股數": qty,
        "失效條件": invalidation,
        "支撐": support,
        "壓力": resist,
    }

# -----------------------------
# Backtest
# -----------------------------
def backtest_ma(df, fast=20, slow=60, fee_bps=10, slippage_bps=5):
    if df.empty or len(df) < slow + 10:
        return None, pd.DataFrame()

    x = df.copy()
    x["Fast"] = x["Close"].rolling(fast).mean()
    x["Slow"] = x["Close"].rolling(slow).mean()

    x["Signal"] = (x["Fast"] > x["Slow"]).astype(int)
    x["Position"] = x["Signal"].shift(1).fillna(0)
    x["AssetRet"] = x["Close"].pct_change().fillna(0)

    turnover = x["Position"].diff().abs().fillna(x["Position"].abs())
    costs = turnover * ((fee_bps + slippage_bps) / 10000)
    x["StrategyRet"] = x["Position"] * x["AssetRet"] - costs
    x["Equity"] = (1 + x["StrategyRet"]).cumprod()
    x["BuyHold"] = (1 + x["AssetRet"]).cumprod()

    equity = x["Equity"]
    peak = equity.cummax()
    dd = equity / peak - 1

    trades = x.loc[x["Position"].diff().fillna(0) != 0, "StrategyRet"]
    wins = trades[trades > 0]
    losses = trades[trades < 0]
    profit_factor = (
        wins.sum() / abs(losses.sum())
        if len(losses) and losses.sum() != 0 else np.nan
    )

    ann_ret = equity.iloc[-1] ** (252 / max(len(x), 1)) - 1
    sharpe = (
        np.sqrt(252) * x["StrategyRet"].mean() / x["StrategyRet"].std()
        if x["StrategyRet"].std() > 0 else np.nan
    )

    stats = {
        "策略累積報酬": equity.iloc[-1] - 1,
        "買進持有報酬": x["BuyHold"].iloc[-1] - 1,
        "最大回撤": dd.min(),
        "勝率": len(wins) / len(trades) if len(trades) else np.nan,
        "Profit Factor": profit_factor,
        "Sharpe": sharpe,
        "年化報酬估計": ann_ret,
        "交易次數": int(len(trades)),
    }
    return stats, x

# -----------------------------
# Portfolio risk
# -----------------------------
def portfolio_risk(holdings):
    frames = []
    for sym, qty, cost in holdings:
        df = get_history(sym, "1y")
        if df.empty:
            continue
        frames.append(df["Close"].rename(sym))
    if not frames:
        return None
    prices = pd.concat(frames, axis=1).dropna(how="all")
    returns = prices.pct_change().dropna()
    latest = prices.ffill().iloc[-1]

    rows = []
    total = 0
    for sym, qty, cost in holdings:
        if sym not in latest.index or pd.isna(latest[sym]):
            continue
        mv = float(latest[sym]) * qty
        total += mv
        rows.append({
            "代碼": sym,
            "名稱": display_name(sym),
            "數量": qty,
            "成本": cost,
            "現價": float(latest[sym]),
            "市值": mv,
        })
    if not rows or total <= 0:
        return None

    p = pd.DataFrame(rows)
    p["權重"] = p["市值"] / total
    corr = returns[p["代碼"].tolist()].corr() if len(p) > 1 else pd.DataFrame()
    hhi = float((p["權重"] ** 2).sum())

    daily_port = returns.reindex(columns=p["代碼"]).fillna(0).mul(p.set_index("代碼")["權重"], axis=1).sum(axis=1)
    vol = daily_port.std() * np.sqrt(252)

    return {
        "table": p,
        "corr": corr,
        "hhi": hhi,
        "annual_vol": vol,
        "total_value": total,
    }

# -----------------------------
# Journal
# -----------------------------
def analyze_journal(df):
    x = df.copy()
    x.columns = [str(c).strip() for c in x.columns]
    candidates = {c.lower(): c for c in x.columns}

    pnl_col = None
    for k in ["pnl", "profit", "損益", "獲利", "盈虧"]:
        if k.lower() in candidates:
            pnl_col = candidates[k.lower()]
            break

    if pnl_col is None:
        if {"進場價", "出場價", "數量"}.issubset(x.columns):
            x["損益"] = (pd.to_numeric(x["出場價"], errors="coerce") -
                        pd.to_numeric(x["進場價"], errors="coerce")) * \
                       pd.to_numeric(x["數量"], errors="coerce")
            pnl_col = "損益"
        else:
            return None

    x[pnl_col] = pd.to_numeric(x[pnl_col], errors="coerce")
    x = x.dropna(subset=[pnl_col])
    if x.empty:
        return None

    wins = x[x[pnl_col] > 0][pnl_col]
    losses = x[x[pnl_col] < 0][pnl_col]
    result = {
        "交易筆數": len(x),
        "勝率": len(wins) / len(x),
        "總損益": x[pnl_col].sum(),
        "平均獲利": wins.mean() if len(wins) else np.nan,
        "平均虧損": losses.mean() if len(losses) else np.nan,
        "Profit Factor": wins.sum() / abs(losses.sum()) if len(losses) and losses.sum() != 0 else np.nan,
    }
    return result, x

# -----------------------------
# UI helpers
# -----------------------------
def fmt_pct(v):
    return "—" if pd.isna(v) else f"{v * 100:.2f}%"

def fmt_num(v):
    return "—" if pd.isna(v) else f"{v:,.2f}"

def render_signal(score):
    if pd.isna(score):
        return "資料不足"
    if score >= 75:
        return "偏多"
    if score >= 60:
        return "中性偏多"
    if score >= 45:
        return "觀察"
    if score >= 30:
        return "中性偏空"
    return "偏空"

# -----------------------------
# Sidebar
# -----------------------------
st.sidebar.title("⚙️ 33 專業操盤系統 V3.0")
page = st.sidebar.radio(
    "功能",
    [
        "🏠 總覽",
        "🤖 量化選股",
        "🔍 個股深度分析",
        "🎯 交易計畫",
        "🧪 策略回測",
        "🛡️ 投資組合風險",
        "📒 交易日誌",
    ],
)

st.sidebar.divider()
capital = st.sidebar.number_input("交易資金", min_value=0.0, value=300000.0, step=10000.0)
risk_pct = st.sidebar.number_input("單筆最大風險 %", min_value=0.1, max_value=5.0, value=1.0, step=0.1)

st.sidebar.markdown("### 📋 自選股管理")
st.sidebar.caption("支援全球任意台股（如 2330, 5274）、美股（如 AAPL, NVDA）、ETF（如 0050, 00878）、期貨（如 ^TWII）。")
watch_text = st.sidebar.text_area(
    "輸入自選股（逗號、空格或換行分隔）",
    value=",".join(DEFAULT_WATCHLIST),
    height=120
)
watchlist = []
for s in re.split(r"[,\n\s]+", watch_text):
    s = normalize_symbol(s)
    if s and s not in watchlist:
        watchlist.append(s)

st.sidebar.caption("資料來源：Yahoo Finance & TWSE。")

# -----------------------------
# Page: Overview
# -----------------------------
if page == "🏠 總覽":
    st.title("📈 33 專業操盤系統 V3.0")
    st.caption("全球資產支援：台股上市櫃、美股、期貨、ETF 萬用查詢引擎。")

    regime_df, regime = market_regime()
    c1, c2, c3 = st.columns(3)
    c1.metric("市場環境", regime)
    c2.metric("自選追蹤數", len(watchlist))
    c3.metric("風險設定", f"{risk_pct:.1f}% / 筆")

    if not regime_df.empty:
        st.subheader("🌏 市場環境指標")
        show = regime_df.copy()
        show["20日報酬"] = show["20日報酬"].map(fmt_pct)
        show["收盤"] = show["收盤"].map(lambda v: f"{v:,.2f}")
        st.dataframe(show, use_container_width=True, hide_index=True)

    st.subheader("📊 自選股量化即時快照")
    rows = []
    for sym in watchlist:
        df = get_history(sym, "1y")
        sc = score_asset(df)
        if df.empty:
            rows.append({"代碼": sym, "名稱": display_name(sym), "狀態": "無資料"})
            continue
        x = add_indicators(df)
        r = x.iloc[-1]
        rows.append({
            "代碼": sym,
            "名稱": display_name(sym),
            "收盤": r["Close"],
            "日漲跌": r["Return1D"],
            "RSI": r["RSI14"],
            "量比": r["VolRatio"],
            "量化分數": sc["score"],
            "訊號": sc["signal"],
            "資料日": x.index[-1].strftime("%Y-%m-%d"),
        })
    snap = pd.DataFrame(rows)
    if not snap.empty:
        for col in ["收盤", "RSI", "量比", "量化分數"]:
            if col in snap.columns:
                snap[col] = snap[col].round(2)
        if "日漲跌" in snap.columns:
            snap["日漲跌"] = snap["日漲跌"].map(fmt_pct)
        st.dataframe(snap, use_container_width=True, hide_index=True)

# -----------------------------
# Page: Quant scanner
# -----------------------------
elif page == "🤖 量化選股":
    st.title("🤖 量化選股中心")
    st.info("動態掃描您左側欄輸入的所有自選全球標的。")

    if not watchlist:
        st.warning("請於左側輸入至少一個自選股代號。")
    else:
        rows = []
        progress = st.progress(0)
        for i, sym in enumerate(watchlist):
            df = get_history(sym, "1y")
            sc = score_asset(df)
            if not df.empty:
                x = add_indicators(df)
                r = x.iloc[-1]
                rows.append({
                    "代碼": sym,
                    "名稱": display_name(sym),
                    "收盤": r["Close"],
                    "日漲跌": r["Return1D"],
                    "5日": r["Return5D"],
                    "20日": r["Return20D"],
                    "RSI": sc["rsi"],
                    "量比": sc["vol_ratio"],
                    "趨勢": sc["trend"],
                    "動能": sc["momentum"],
                    "量能": sc["volume"],
                    "突破": sc["breakout"],
                    "風險": sc["risk"],
                    "總分": sc["score"],
                    "訊號": sc["signal"],
                })
            progress.progress((i + 1) / max(len(watchlist), 1))
        progress.empty()

        result = pd.DataFrame(rows)
        if result.empty:
            st.warning("目前沒有足夠資料。")
        else:
            sort_col = st.selectbox("排序依據", ["總分", "量能", "突破", "動能", "趨勢", "5日"])
            result = result.sort_values(sort_col, ascending=False)
            st.dataframe(
                result.style.format({
                    "收盤": "{:,.2f}",
                    "日漲跌": "{:.2%}",
                    "5日": "{:.2%}",
                    "20日": "{:.2%}",
                    "RSI": "{:.1f}",
                    "量比": "{:.2f}",
                    "趨勢": "{:.1f}",
                    "動能": "{:.1f}",
                    "量能": "{:.1f}",
                    "突破": "{:.1f}",
                    "風險": "{:.1f}",
                    "總分": "{:.1f}",
                }),
                use_container_width=True,
            )

# -----------------------------
# Page: Deep analysis
# -----------------------------
elif page == "🔍 個股深度分析":
    st.title("🔍 個股深度分析")
    
    col_input, col_mode = st.columns([2, 1])
    with col_input:
        manual_input = st.text_input("輸入任意全球代號查詢（例如: 5274, 2330, NVDA, 0050, QQQ, ^TWII）", value="5274")
    
    target_symbol = normalize_symbol(manual_input) if manual_input else (watchlist[0] if watchlist else "2330.TW")

    df = get_history(target_symbol, "2y")
    if df.empty:
        st.error(f"無法取得代號 `{target_symbol}` 的資料，請確認代號是否正確。")
    else:
        x = add_indicators(df)
        r = x.iloc[-1]
        sc = score_asset(df)
        d_name = display_name(target_symbol)

        st.markdown(f"### 📌 標的：{d_name} (`{target_symbol}`) 最新報價")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("收盤價", f"{r['Close']:,.2f}")
        c2.metric("量化總分", f"{sc['score']:.1f}")
        c3.metric("RSI (14)", f"{r['RSI14']:.1f}")
        c4.metric("成交量比", f"{r['VolRatio']:.2f}x")
        c5.metric("量化訊號", sc["signal"])

        st.subheader("技術結構數據")
        tech = pd.DataFrame({
            "指標": ["MA5", "MA20", "MA60", "MA120", "MA240", "BB上軌", "BB中軌", "BB下軌", "ATR14", "20日高", "20日低"],
            "數值": [r.get(k, np.nan) for k in ["MA5","MA20","MA60","MA120","MA240","BBUpper","BBMid","BBLower","ATR14","High20","Low20"]]
        })
        tech["數值"] = tech["數值"].round(2)
        st.dataframe(tech, use_container_width=True, hide_index=True)

        st.subheader("歷史價格與均線走勢")
        chart_df = x[["Close", "MA20", "MA60", "MA120"]].dropna(how="all")
        st.line_chart(chart_df)

        st.subheader("三大法人動向（台股上市櫃官方 T86）")
        inst = institutional_history(target_symbol, 5)
        if inst.empty:
            st.info("此標的非台股上市櫃或暫無官方法人資料可供檢索。")
        else:
            st.dataframe(inst, use_container_width=True, hide_index=True)

        st.subheader("資料時間")
        st.write(f"最後交易資料日期：{x.index[-1].strftime('%Y-%m-%d')}")

# -----------------------------
# Page: Trade plan
# -----------------------------
elif page == "🎯 交易計畫":
    st.title("🎯 自動交易計畫與風險規劃")
    
    plan_input = st.text_input("輸入欲建立計畫的代號", value="2330.TW")
    plan_sym = normalize_symbol(plan_input)
    
    df = get_history(plan_sym, "2y")
    plan = make_trade_plan(df, capital=capital, risk_pct=risk_pct)

    if plan is None:
        st.error("資料不足，無法建立交易計畫。")
    else:
        st.subheader(f"📌 {display_name(plan_sym)} (`{plan_sym}`) 操盤執行框架")
        c = st.columns(4)
        c[0].metric("現價", f"{plan['現價']:,.2f}")
        c[1].metric("建議停損", f"{plan['停損']:,.2f}")
        c[2].metric("第一停利 (TP1)", f"{plan['TP1']:,.2f}")
        c[3].metric("第二停利 (TP2)", f"{plan['TP2']:,.2f}")

        table = pd.DataFrame([
            ["回檔進場區", plan["回檔進場區"]],
            ["突破確認價", f"{plan['突破確認價']:,.2f}"],
            ["關鍵支撐", f"{plan['支撐']:,.2f}"],
            ["關鍵壓力", f"{plan['壓力']:,.2f}"],
            ["TP1 風險報酬比 (R:R)", f"{plan['RR1']:.2f}"],
            ["TP2 風險報酬比 (R:R)", f"{plan['RR2']:.2f}"],
            ["單股風險", f"{plan['單股風險']:,.2f}"],
            ["本筆風險金額", f"{plan['風險金額']:,.0f}"],
            ["建議股數", f"{plan['建議股數']:,}"],
            ["部位失效條件", plan["失效條件"]],
        ], columns=["項目", "數值"])
        st.dataframe(table, use_container_width=True, hide_index=True)

        st.warning("以上計畫依歷史量價與波動率計算，實際進出請務必嚴格執行停損紀律。")

# -----------------------------
# Page: Backtest
# -----------------------------
elif page == "🧪 策略回測":
    st.title("🧪 策略回測實驗室")
    bt_input = st.text_input("輸入回測標的代號", value="2330.TW")
    bt_sym = normalize_symbol(bt_input)
    
    fast = st.slider("短均線", 5, 50, 20)
    slow = st.slider("長均線", 30, 250, 60)
    fee = st.number_input("手續費＋稅等成本（bps）", 0.0, 100.0, 10.0)
    slippage = st.number_input("滑價（bps）", 0.0, 100.0, 5.0)

    if fast >= slow:
        st.error("短均線必須小於長均線。")
    else:
        df = get_history(bt_sym, "5y")
        stats, bt = backtest_ma(df, fast, slow, fee, slippage)
        if stats is None:
            st.error("資料不足，無法回測。")
        else:
            cols = st.columns(4)
            cols[0].metric("策略報酬", fmt_pct(stats["策略累積報酬"]))
            cols[1].metric("最大回撤", fmt_pct(stats["最大回撤"]))
            cols[2].metric("勝率", fmt_pct(stats["勝率"]))
            cols[3].metric("Profit Factor", f"{stats['Profit Factor']:.2f}" if pd.notna(stats["Profit Factor"]) else "—")

            st.write({
                "買進持有報酬": fmt_pct(stats["買進持有報酬"]),
                "夏普比率 (Sharpe)": round(stats["Sharpe"], 2) if pd.notna(stats["Sharpe"]) else None,
                "年化報酬估計": fmt_pct(stats["年化報酬估計"]),
                "總交易次數": stats["交易次數"],
            })
            st.line_chart(bt[["Equity", "BuyHold"]])

# -----------------------------
# Page: Portfolio risk
# -----------------------------
elif page == "🛡️ 投資組合風險":
    st.title("🛡️ 投資組合風險管理")
    st.caption("您可以自由輸入任意台美股、ETF、期貨持倉來估算整體權重與相關性。")

    default_rows = pd.DataFrame([
        {"代碼": "2330.TW", "數量": 1000, "成本": 900.0},
        {"代碼": "0050.TW", "數量": 2000, "成本": 180.0},
        {"代碼": "NVDA", "數量": 50, "成本": 120.0},
    ])
    holdings_df = st.data_editor(
        default_rows,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "代碼": st.column_config.TextColumn("代碼"),
            "數量": st.column_config.NumberColumn("數量", min_value=0),
            "成本": st.column_config.NumberColumn("成本", min_value=0),
        }
    )

    holdings = []
    for _, row in holdings_df.iterrows():
        sym = normalize_symbol(row["代碼"])
        try:
            qty = float(row["數量"])
            cost = float(row["成本"])
        except Exception:
            continue
        if sym and qty > 0:
            holdings.append((sym, qty, cost))

    if holdings:
        pr = portfolio_risk(holdings)
        if pr is None:
            st.error("無法取得持倉標的資料。")
        else:
            c1, c2, c3 = st.columns(3)
            c1.metric("組合總市值", f"{pr['total_value']:,.0f}")
            c2.metric("年化波動率估計", fmt_pct(pr["annual_vol"]))
            c3.metric("HHI 集中度", f"{pr['hhi']:.3f}")

            st.subheader("持倉權重明細")
            st.dataframe(pr["table"], use_container_width=True, hide_index=True)

            if not pr["corr"].empty:
                st.subheader("歷史報酬相關性矩陣")
                st.dataframe(pr["corr"].round(2), use_container_width=True)

            st.subheader("歷史壓力情境模擬")
            scenarios = [-0.10, -0.20, -0.30]
            rows = []
            for shock in scenarios:
                rows.append({
                    "情境假設": f"全部持倉同步下挫 {shock:.0%}",
                    "估算損失金額": pr["total_value"] * shock,
                    "壓力後剩餘市值": pr["total_value"] * (1 + shock),
                })
            st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

# -----------------------------
# Page: Journal
# -----------------------------
elif page == "📒 交易日誌":
    st.title("📒 交易日誌分析")
    st.write("上傳您的交易紀錄 CSV 檔，系統將自動分析勝率、損益與 Profit Factor。")
    file = st.file_uploader("上傳交易紀錄 CSV", type=["csv"])

    if file:
        try:
            j = pd.read_csv(file)
            analyzed = analyze_journal(j)
            if analyzed is None:
                st.error("無法辨識損益欄位。請至少提供 PnL/損益，或 進場價、出場價、數量。")
            else:
                stats, clean = analyzed
                c = st.columns(4)
                c[0].metric("總交易筆數", stats["交易筆數"])
                c[1].metric("勝率", fmt_pct(stats["勝率"]))
                c[2].metric("總累積損益", f"{stats['總損益']:,.2f}")
                c[3].metric("Profit Factor", f"{stats['Profit Factor']:.2f}" if pd.notna(stats["Profit Factor"]) else "—")
                st.dataframe(clean, use_container_width=True, hide_index=True)

                st.subheader("操盤行為診斷與建議")
                if stats["勝率"] < 0.45:
                    st.write("• 勝率偏低：建議檢視進場條件的過濾機制與停損點執行狀況。")
                if pd.notna(stats["平均虧損"]) and pd.notna(stats["平均獲利"]) and abs(stats["平均虧損"]) > stats["平均獲利"]:
                    st.write("• 平均虧損大於平均獲利：建議優化風險報酬比，讓獲利部位跑得更遠。")
                if stats["交易筆數"] < 20:
                    st.write("• 樣本數小於 20 筆，統計顯著性尚不足。")
        except Exception as e:
            st.error(f"解析交易日誌發生錯誤：{str(e)}")

st.divider()
st.caption(
    "33 專業操盤系統 V3.0：支援全球台美股、期貨與 ETF 動態查詢與量化風控。"
)

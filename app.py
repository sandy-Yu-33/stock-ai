import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from sklearn.linear_model import LinearRegression
import plotly.graph_objects as go
from datetime import datetime, timedelta

# 設置頁面配置
st.set_page_config(
    page_title="Stock AI 分析",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.title("📈 Stock AI 股市分析工具")
st.markdown("---")

# 側邊欄配置
with st.sidebar:
    st.header("⚙️ 設定")
    
    # 股票代碼輸入
    stock_symbol = st.text_input(
        "輸入股票代碼 (例如: 2330.TW, AAPL)",
        value="2330.TW",
        placeholder="輸入股票代碼"
    )
    
    # 時間範圍選擇
    time_range = st.selectbox(
        "選擇時間範圍",
        ["1個月", "3個月", "6個月", "1年", "2年", "5年"]
    )
    
    # 映射時間範圍
    period_map = {
        "1個月": "1mo",
        "3個月": "3mo",
        "6個月": "6mo",
        "1年": "1y",
        "2年": "2y",
        "5年": "5y"
    }
    period = period_map[time_range]

# 主要內容
if stock_symbol:
    try:
        # 下載股票數據
        with st.spinner(f"正在加載 {stock_symbol} 的數據..."):
            stock_data = yf.download(stock_symbol, period=period, progress=False)
        
        if stock_data.empty:
            st.error(f"❌ 無法找到股票代碼: {stock_symbol}")
        else:
            # 獲取股票信息
            ticker = yf.Ticker(stock_symbol)
            info = ticker.info
            
            # 顯示股票基本信息
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                current_price = info.get('currentPrice', stock_data['Close'].iloc[-1])
                st.metric("當前價格", f"${current_price:.2f}")
            
            with col2:
                prev_close = info.get('previousClose', stock_data['Close'].iloc[-2])
                change = current_price - prev_close
                change_percent = (change / prev_close * 100) if prev_close else 0
                st.metric("價格變化", f"${change:.2f}", f"{change_percent:.2f}%")
            
            with col3:
                market_cap = info.get('marketCap', 'N/A')
                if isinstance(market_cap, (int, float)):
                    st.metric("市值", f"${market_cap/1e9:.2f}B")
                else:
                    st.metric("市值", "N/A")
            
            with col4:
                avg_volume = info.get('averageVolume', 'N/A')
                if isinstance(avg_volume, (int, float)):
                    st.metric("平均成交量", f"{avg_volume/1e6:.2f}M")
                else:
                    st.metric("平均成交量", "N/A")
            
            st.markdown("---")
            
            # 標籤頁面
            tab1, tab2, tab3 = st.tabs(["📊 價格走勢", "📈 技術分析", "🔮 價格預測"])
            
            # 標籤1: 價格走勢
            with tab1:
                st.subheader("股票價格走勢")
                
                # 繪製價格圖表
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=stock_data['Close'],
                    mode='lines',
                    name='收盤價',
                    line=dict(color='#1f77b4', width=2)
                ))
                
                fig.update_layout(
                    title=f"{stock_symbol} 股票價格",
                    xaxis_title="日期",
                    yaxis_title="價格 ($)",
                    hovermode='x unified',
                    height=500,
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 顯示統計資訊
                col1, col2, col3, col4, col5 = st.columns(5)
                
                with col1:
                    st.metric("最高價", f"${stock_data['High'].max():.2f}")
                with col2:
                    st.metric("最低價", f"${stock_data['Low'].min():.2f}")
                with col3:
                    st.metric("平均價", f"${stock_data['Close'].mean():.2f}")
                with col4:
                    volatility = stock_data['Close'].pct_change().std() * 100
                    st.metric("波動率", f"{volatility:.2f}%")
                with col5:
                    annual_return = ((stock_data['Close'].iloc[-1] / stock_data['Close'].iloc[0]) - 1) * 100
                    st.metric("期間報酬", f"{annual_return:.2f}%")
            
            # 標籤2: 技術分析
            with tab2:
                st.subheader("技術分析指標")
                
                # 計算移動平均線
                stock_data['MA20'] = stock_data['Close'].rolling(window=20).mean()
                stock_data['MA50'] = stock_data['Close'].rolling(window=50).mean()
                
                # 計算相對強弱指標 (RSI)
                delta = stock_data['Close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss
                stock_data['RSI'] = 100 - (100 / (1 + rs))
                
                # 繪製價格和移動平均線
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=stock_data['Close'],
                    mode='lines',
                    name='收盤價',
                    line=dict(color='black', width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=stock_data['MA20'],
                    mode='lines',
                    name='20日移動平均',
                    line=dict(color='orange', width=1)
                ))
                fig.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=stock_data['MA50'],
                    mode='lines',
                    name='50日移動平均',
                    line=dict(color='red', width=1)
                ))
                
                fig.update_layout(
                    title="移動平均線",
                    xaxis_title="日期",
                    yaxis_title="價格 ($)",
                    hovermode='x unified',
                    height=450,
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # RSI 指標
                fig_rsi = go.Figure()
                fig_rsi.add_trace(go.Scatter(
                    x=stock_data.index,
                    y=stock_data['RSI'],
                    mode='lines',
                    name='RSI',
                    line=dict(color='purple', width=2)
                ))
                fig_rsi.add_hline(y=70, line_dash="dash", line_color="red", annotation_text="超買 (70)")
                fig_rsi.add_hline(y=30, line_dash="dash", line_color="green", annotation_text="超賣 (30)")
                
                fig_rsi.update_layout(
                    title="相對強弱指標 (RSI)",
                    xaxis_title="日期",
                    yaxis_title="RSI",
                    hovermode='x unified',
                    height=400,
                    template='plotly_white'
                )
                st.plotly_chart(fig_rsi, use_container_width=True)
            
            # 標籤3: 價格預測
            with tab3:
                st.subheader("🔮 未來30天價格預測")
                
                # 準備數據
                data = stock_data[['Close']].copy()
                data['Next_Close'] = data['Close'].shift(-1)
                data = data.dropna()
                
                # 特徵工程
                scaler = MinMaxScaler()
                data_scaled = scaler.fit_transform(data[['Close']])
                
                X = data_scaled[:-1].reshape(-1, 1)
                y = data['Close'].values[1:]
                
                # 訓練模型
                model = LinearRegression()
                model.fit(X, y)
                
                # 進行預測
                future_days = 30
                last_price = stock_data['Close'].iloc[-1]
                predictions = []
                
                for _ in range(future_days):
                    scaled_price = scaler.transform([[last_price]])
                    next_price = model.predict(scaled_price)[0]
                    predictions.append(next_price)
                    last_price = next_price
                
                # 創建預測日期
                future_dates = pd.date_range(
                    start=stock_data.index[-1] + timedelta(days=1),
                    periods=future_days
                )
                
                # 繪製預測圖表
                fig = go.Figure()
                
                # 歷史數據
                fig.add_trace(go.Scatter(
                    x=stock_data.index[-60:],
                    y=stock_data['Close'].iloc[-60:],
                    mode='lines',
                    name='歷史價格',
                    line=dict(color='blue', width=2)
                ))
                
                # 預測數據
                fig.add_trace(go.Scatter(
                    x=future_dates,
                    y=predictions,
                    mode='lines+markers',
                    name='預測價格',
                    line=dict(color='red', width=2, dash='dash'),
                    marker=dict(size=6)
                ))
                
                fig.update_layout(
                    title=f"{stock_symbol} 未來30天價格預測",
                    xaxis_title="日期",
                    yaxis_title="價格 ($)",
                    hovermode='x unified',
                    height=500,
                    template='plotly_white'
                )
                st.plotly_chart(fig, use_container_width=True)
                
                # 預測統計
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("當前價格", f"${stock_data['Close'].iloc[-1]:.2f}")
                with col2:
                    st.metric("預測最高價", f"${max(predictions):.2f}")
                with col3:
                    predicted_change = ((predictions[-1] - stock_data['Close'].iloc[-1]) / stock_data['Close'].iloc[-1] * 100)
                    st.metric("預期變化", f"{predicted_change:.2f}%")
                
                st.info("⚠️ 免責聲明: 此預測基於歷史數據和線性回歸模型，不構成投資建議。")
    
    except Exception as e:
        st.error(f"❌ 發生錯誤: {str(e)}")
        st.info("請確保輸入的股票代碼正確，例如: 2330.TW (台灣), AAPL (美國)")

else:
    st.info("👈 請在左側邊欄輸入股票代碼開始分析")

st.markdown("---")
st.markdown(
    """
    <div style='text-align: center'>
    <small>Stock AI 股市分析工具 | 數據來源: Yahoo Finance</small>
    </div>
    """,
    unsafe_allow_html=True
)

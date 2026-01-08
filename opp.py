import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# 1. API 配置
if "YOUR_GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["YOUR_GEMINI_API_KEY"]
    genai.configure(api_key=api_key.strip())
else:
    st.error("❌ 錯誤：請在 Streamlit Cloud 的 Secrets 中設定 YOUR_GEMINI_API_KEY")
    st.stop()

# 2. 初始化清單
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["MU", "NVDA", "2408.TW", "SMR", "PLTR"]

# --- 核心數據函數 (新增 FKD 計算) ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # 抓取 3 個月數據以確保指標計算準確
        hist = stock.history(period="3mo")
        if hist.empty:
            return pd.DataFrame()
        
        # --- 計算 FKD (Stochastic Oscillator) ---
        low_14 = hist['Low'].rolling(window=14).min()
        high_14 = hist['High'].rolling(window=14).max()
        
        # Fast K% = (當前收盤 - 14日最低) / (14日最高 - 14日最低) * 100
        hist['Fast_K'] = (hist['Close'] - low_14) / (high_14 - low_14) * 100
        # Fast D% = Fast K% 的 3 日移動平均
        hist['Fast_D'] = hist['Fast_K'].rolling(window=3).mean()
        
        return hist.tail(30) # 只回傳最近 30 天顯示
    except Exception as e:
        st.error(f"無法抓取 {ticker}: {e}")
        return pd.DataFrame()

# --- 核心 AI 分析函數 ---
def generate_ai_report(tickers):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    market_context = f"【報告日期】：{current_date}\n\n"
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            price_data = stock.history(period="1d")
            price = price_data['Close'].iloc[-1] if not price_data.empty else 0
            news_list = stock.news
            news_summary = ""
            if news_list:
                for n in news_list[:2]:
                    title = n.get('title') or n.get('summary') or "無標題資訊"
                    news_summary += f"  - {title}\n"
            else:
                news_summary = "  - (無近期新聞)\n"
            market_context += f"股票 {t} (現價: ${price:.2f}):\n{news_summary}\n"
        except:
            continue

    prompt = f"你是一位華爾街資深分析師。今天是 {current_date}。請根據以下數據寫一份繁體中文投資日報，禁止使用程式碼區塊，直接輸出文字報告：\n{market_context}"

    models_to_try = ["models/gemini-3-flash-preview", "models/gemini-2.0-flash", "models/gemini-flash-latest"]
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```markdown", "").replace("```text", "").replace("```", "")
            return f"✅ 分析成功 (使用模型: {model_name})\n\n" + clean_text.strip()
        except:
            continue
    return "❌ 所有 AI 模型均忙碌中。"

# --- 網頁介面 ---
st.set_page_config(page_title="2026 AI 戰情室", layout="wide")
st.title("🛡️ 2026 全球 AI 投資戰情室")

# 側邊欄
with st.sidebar:
    st.header("📝 追蹤清單")
    new_ticker = st.text_input("輸入代號", placeholder="AAPL")
    if st.button("新增") and new_ticker:
        if new_ticker.upper() not in st.session_state.my_watchlist:
            st.session_state.my_watchlist.append(new_ticker.upper())
            st.rerun()
    st.write("---")
    for t in st.session_state.my_watchlist:
        c1, c2 = st.columns([0.8, 0.2])
        c1.write(f"**{t}**")
        if c2.button("X", key=f"del_{t}"):
            st.session_state.my_watchlist.remove(t)
            st.rerun()

# --- 強化繪圖區 ---
st.subheader("📊 價格走勢與 FKD 指標")
if st.session_state.my_watchlist:
    for t in st.session_state.my_watchlist:
        hist = get_stock_data(t)
        if not hist.empty:
            # 建立雙 Y 軸圖表 (上方價格，下方指標)
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.1, subplot_titles=(f"{t} 股價", "快速隨機指標 FKD"),
                               row_heights=[0.7, 0.3])

            # 1. 價格線
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='收盤價', line=dict(color='#00CC96')), row=1, col=1)
            
            # 2. FKD 指標線
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_K'], name='Fast K%', line=dict(color='#FF4B4B', dash='dot')), row=2, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_D'], name='Fast D%', line=dict(color='#31333F')), row=2, col=1)
            
            # 3. 加入超買/超賣水平線 (80/20)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=2, col=1)

            fig.update_layout(height=500, showlegend=True, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# AI 分析
st.subheader("🤖 AI 首席策略師分析")
if st.button("🚀 啟動全市場掃描", type="primary"):
    with st.spinner("AI 正在深度分析中..."):
        report = generate_ai_report(st.session_state.my_watchlist)
        st.success("分析完成！")
        st.markdown(report)

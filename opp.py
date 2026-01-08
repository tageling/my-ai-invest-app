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
    st.error("❌ 錯誤：請在 Secrets 中設定 YOUR_GEMINI_API_KEY")
    st.stop()

# 2. 初始化清單 (預設包含你最關注的標的)
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["MU", "NVDA", "TSLA", "SMR", "PLTR", "VST"]

# --- 核心數據函數 ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo")
        if hist.empty: return pd.DataFrame()
        
        # 計算 FKD 與量價指標
        low_14 = hist['Low'].rolling(window=14).min()
        high_14 = hist['High'].rolling(window=14).max()
        hist['Fast_K'] = (hist['Close'] - low_14) / (high_14 - low_14) * 100
        hist['Fast_D'] = hist['Fast_K'].rolling(window=3).mean()
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['Vol_MA20'] = hist['Volume'].rolling(window=20).mean()
        hist['Vol_Ratio'] = hist['Volume'] / hist['Vol_MA20']
        
        return hist.tail(90) # 維持 3 個月顯示
    except:
        return pd.DataFrame()

# --- 【深度進化】核心 AI 分析函數 ---
def generate_ai_report(tickers):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    # 彙整清單數據上下文
    market_context = ""
    for t in tickers:
        hist = get_stock_data(t)
        if not hist.empty:
            last = hist.iloc[-1]
            status = "多頭排列" if last['Close'] > last['MA20'] else "低位修正"
            vol_msg = "🔥【量能異常放大】" if last['Vol_Ratio'] > 1.5 else "量能平穩"
            market_context += f"- {t}: 現價{last['Close']:.2f}, 趨勢:{status}, 籌碼:{vol_msg}, FKD:{last['Fast_K']:.1f}\n"

    # 深度獵殺 Prompt：結合清單深度診斷與全球黑馬搜尋
    prompt = f"""
    你是一位擁有 20 年資歷的首席量化分析師。今天是 {current_date}。
    
    【任務一：既有清單深度診斷】
    請針對以下追蹤清單中的『每一隻標的』，結合最新的財報、全球財經新聞、籌碼量比與 FKD 指標給出詳細分析：
    {market_context}
    
    特別要求：
    - 針對 VST, TSLA, NVDA 進行基本面與技術面的共振分析。
    - 判斷目前的震盪（如 VST 近期的重挫或 TSLA 的數據波動）是「基本面惡化」還是「技術面修正」。
    - 提及分析師目標價與機構資金流向。

    【任務二：全球黑馬獵殺】
    主動跳出清單，搜尋 2026 年全球 AI 產業鏈中，目前具備『資訊共振』的 2 隻爆發標的。
    題材：液冷散熱、ASIC 自研晶片 (如 Marvell)、或 AI 能源基礎設施。

    格式美化要求 (嚴格執行)：
    1. 【標題美化】：請在所有大標題加上 :blue-background[文字內容]。
    2. 【標的突出】：提及股票代號時，請使用 :orange[代號]。
    3. 【建議標籤】：針對建議，請務必使用徽章標籤，例如 :green-badge[強烈建議買入]、:red-badge[建議減碼]、:violet-badge[低位攤平]、:gray-badge[觀望]。
    4. 【數據強調】：重要的數值（如量比、FKD）請用 :violet[數值] 標示。
    5. 【禁止行為】：使用繁體中文，禁止使用任何程式碼區塊標記 (如 ```)，直接輸出。
    """

    models_to_try = ["models/gemini-3-flash-preview", "models/gemini-2.0-flash"]
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```markdown", "").replace("```text", "").replace("```", "")
            return f"✅ 深度全球獵殺報告完成 (使用模型: {model_name})\n\n" + clean_text.strip()
        except:
            continue
    return "❌ 掃描失敗，請檢查網路或金鑰。"

# --- 網頁介面 (維持 Golden V1.0 樣式) ---
st.set_page_config(page_title="2026 AI 全球獵殺戰情室 (深度版)", layout="wide")
st.title("🏹 2026 AI 全球獵殺戰情室")

with st.sidebar:
    st.header("📝 追蹤清單")
    new_ticker = st.text_input("輸入代號", placeholder="VST")
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

st.subheader("📊 技術指標監控 (價格 & FKD)")
if st.session_state.my_watchlist:
    for t in st.session_state.my_watchlist:
        hist = get_stock_data(t)
        if not hist.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=(f"{t} 股價", "快速隨機指標 FKD"), row_heights=[0.7, 0.3])
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='收盤價', line=dict(color='#00CC96')), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_K'], name='Fast K%', line=dict(color='#FF4B4B', dash='dot')), row=2, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_D'], name='Fast D%', line=dict(color='#31333F')), row=2, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=2, col=1)
            fig.update_layout(height=450, showlegend=True, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("🤖 AI 首席策略師深度解析")
if st.button("🚀 啟動全市場 AI 深度獵殺掃描", type="primary"):
    with st.spinner("AI 正在解析清單標的基本面與全球籌碼流向..."):
        report = generate_ai_report(st.session_state.my_watchlist)
        st.success("分析完成！")
        st.markdown(report)

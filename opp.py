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

# 2. 初始化清單
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["MU", "NVDA", "TSLA", "SMR", "PLTR"]

# --- 核心數據函數 (加入籌碼量價邏輯) ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # 抓取 6 個月數據以確保籌碼均線計算準確
        hist = stock.history(period="6mo")
        if hist.empty: return pd.DataFrame()
        
        # --- 計算 FKD ---
        low_14 = hist['Low'].rolling(window=14).min()
        high_14 = hist['High'].rolling(window=14).max()
        hist['Fast_K'] = (hist['Close'] - low_14) / (high_14 - low_14) * 100
        hist['Fast_D'] = hist['Fast_K'].rolling(window=3).mean()
        
        # --- 計算籌碼量價指標 ---
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['Vol_MA20'] = hist['Volume'].rolling(window=20).mean()
        # 量比：今日成交量 / 20日平均量 (判斷是否有大戶進場)
        hist['Vol_Ratio'] = hist['Volume'] / hist['Vol_MA20']
        
        return hist.tail(30)
    except:
        return pd.DataFrame()

# --- 核心 AI 分析函數 (主動獵殺掃描版) ---
def generate_ai_report(tickers):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    # 彙整清單數據供 AI 判斷籌碼
    market_context = ""
    for t in tickers:
        hist = get_stock_data(t)
        if not hist.empty:
            last = hist.iloc[-1]
            status = "多頭排列" if last['Close'] > last['MA20'] else "盤整中"
            vol_msg = "🔥【量能異常放大】" if last['Vol_Ratio'] > 1.5 else "量能平穩"
            market_context += f"- {t}: 現價{last['Close']:.2f}, 趨勢:{status}, 籌碼:{vol_msg}, FKD:{last['Fast_K']:.1f}\n"

    # 設定最強獵殺 Prompt
    prompt = f"""
    你是一位擁有 20 年資歷的首席量化分析師。今天是 {current_date}。
    
    【任務一：清單診斷】
    請針對以下追蹤清單，結合『籌碼量比 (Vol Ratio)』與『FKD 指標』給出具體的買賣建議：
    {market_context}
    
    【任務二：全球黑馬獵殺】
    請主動跳出清單，搜尋 2026 年全球 AI 產業鏈中，目前最具備『資訊共振』的 2 隻爆發標的。
    推薦必須符合：
    1. 題材：液冷散熱、HBM4 封裝、ASIC 自研晶片、或是 2026 年核能電力協議相關。
    2. 籌碼：近期有機構資金明顯流入（成交量異常爆發）。
    3. 技術：FKD 低位轉強。
    
    要求：使用繁體中文，禁止使用程式碼區塊標記，直接輸出專業報告。
    """

    models_to_try = ["models/gemini-3-flash-preview", "models/gemini-2.0-flash", "models/gemini-flash-latest"]
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            clean_text = response.text.replace("```markdown", "").replace("```text", "").replace("```", "")
            return f"✅ 全球掃描完成 (使用模型: {model_name})\n\n" + clean_text.strip()
        except:
            continue
    return "❌ 掃描失敗，請檢查網路或金鑰。"

# --- 網頁介面 ---
st.set_page_config(page_title="2026 AI 全球獵殺戰情室", layout="wide")
st.title("🏹 2026 AI 全球獵殺戰情室")

# 側邊欄
with st.sidebar:
    st.header("📝 追蹤清單")
    new_ticker = st.text_input("輸入代號", placeholder="NVDA")
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

# --- 維持上一版：價格 + FKD 雙圖表樣式 ---
st.subheader("📊 技術指標監控 (價格 & FKD)")
if st.session_state.my_watchlist:
    for t in st.session_state.my_watchlist:
        hist = get_stock_data(t)
        if not hist.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                               vertical_spacing=0.1, subplot_titles=(f"{t} 股價", "快速隨機指標 FKD"),
                               row_heights=[0.7, 0.3])
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='收盤價', line=dict(color='#00CC96')), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_K'], name='Fast K%', line=dict(color='#FF4B4B', dash='dot')), row=2, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_D'], name='Fast D%', line=dict(color='#31333F')), row=2, col=1)
            fig.add_hline(y=80, line_dash="dash", line_color="red", row=2, col=1)
            fig.add_hline(y=20, line_dash="dash", line_color="green", row=2, col=1)
            fig.update_layout(height=500, showlegend=True, margin=dict(l=0, r=0, t=30, b=0))
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# --- 升級版 AI 報告區 ---
st.subheader("🤖 AI 首席策略師分析 (含籌碼判斷與黑馬預測)")
if st.button("🚀 啟動全市場 AI 獵殺掃描", type="primary"):
    with st.spinner("AI 正在解析全球籌碼流向與產業鏈共振標的..."):
        report = generate_ai_report(st.session_state.my_watchlist)
        st.success("掃描完成！")
        st.markdown(report)

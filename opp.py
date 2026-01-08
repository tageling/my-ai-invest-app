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
    st.session_state.my_watchlist = ["MU", "NVDA", "2408.TW", "SMR", "PLTR"]

# --- 核心數據函數 (加入籌碼量價邏輯) ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="6mo") # 抓半年數據判斷長期趨勢
        if hist.empty: return pd.DataFrame()
        
        # 計算 FKD
        low_14 = hist['Low'].rolling(window=14).min()
        high_14 = hist['High'].rolling(window=14).max()
        hist['Fast_K'] = (hist['Close'] - low_14) / (high_14 - low_14) * 100
        hist['Fast_D'] = hist['Fast_K'].rolling(window=3).mean()
        
        # 計算量價籌碼指標
        hist['MA20'] = hist['Close'].rolling(window=20).mean()
        hist['Vol_MA20'] = hist['Volume'].rolling(window=20).mean()
        # 量比：今日成交量 / 20日平均量
        hist['Vol_Ratio'] = hist['Volume'] / hist['Vol_MA20']
        
        return hist.tail(30)
    except:
        return pd.DataFrame()

# --- 核心 AI 分析函數 (主動擴展掃描) ---
def generate_ai_report(tickers):
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    # 彙整清單數據
    market_context = ""
    for t in tickers:
        hist = get_stock_data(t)
        if not hist.empty:
            last = hist.iloc[-1]
            status = "多頭排列" if last['Close'] > last['MA20'] else "區間震盪"
            vol_msg = "【量能激增】" if last['Vol_Ratio'] > 1.5 else "量能平穩"
            market_context += f"- {t}: 現價{last['Close']:.2f}, {status}, {vol_msg}, FKD({last['Fast_K']:.1f})\n"

    # 設定最強 Prompt：要求 AI 搜尋並預測非清單標的
    prompt = f"""
    你是一位擁有 20 年經驗的華爾街首席策略師。今天是 {current_date}。
    
    第一部分：清單診斷
    請針對以下追蹤清單，結合籌碼量價（Vol Ratio）進行診斷：
    {market_context}
    
    第二部分：全球獵殺掃描 (核心任務)
    請根據 2026 年全球 AI 工業化、能源轉型、邊緣運算等大趨勢，主動預測並提供 2-3 隻『清單外』的標的。
    這些標的必須滿足以下『多方資訊共振』條件：
    1. 題材面：具備 2026 年剛需（如液冷、HBM4、SMR核能、光通訊）。
    2. 籌碼面：近期有機構大戶建倉跡象或成交量異常放大。
    3. 技術面：FKD 低位金叉或強勢高位鈍化。
    
    分析要求：
    - 禁止使用程式碼區塊。
    - 使用繁體中文。
    - 標註出你認為的『黑馬爆發潛力股』並說明推薦理由。
    """

    models_to_try = ["models/gemini-3-flash-preview", "models/gemini-2.0-flash", "models/gemini-flash-latest"]
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            return f"✅ 全球掃描完成 (使用模型: {model_name})\n\n" + response.text
        except:
            continue
    return "❌ 掃描失敗。"

# --- 網頁介面 ---
st.set_page_config(page_title="2026 AI 全球獵殺掃描器", layout="wide")
st.title("🏹 2026 AI 全球獵殺掃描器")
st.caption(f"監控範圍：全美股及台股半導體鏈 | 模式：多方資訊共振偵測 | {datetime.now().strftime('%Y-%m-%d')}")

# 圖表顯示 (略，保持原有 FKD 功能)
if st.session_state.my_watchlist:
    st.subheader("📊 清單技術指標 (FKD + 量價)")
    for t in st.session_state.my_watchlist:
        hist = get_stock_data(t)
        if not hist.empty:
            fig = make_subplots(rows=2, cols=1, shared_xaxes=True, subplot_titles=(f"{t} 股價/籌碼量比", "FKD"), row_heights=[0.7, 0.3])
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], name='收盤'), row=1, col=1)
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Fast_K'], name='K%'), row=2, col=1)
            fig.update_layout(height=400)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# AI 核心掃描
st.subheader("🤖 AI 全球資訊共振報告 (含黑馬預測)")
if st.button("🚀 啟動全市場 AI 獵殺掃描", type="primary"):
    with st.spinner("正在檢索 2026 全球產業鏈資訊與籌碼動向..."):
        report = generate_ai_report(st.session_state.my_watchlist)
        st.markdown(report)

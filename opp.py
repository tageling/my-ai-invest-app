import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
from datetime import datetime

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

# --- 核心數據函數 ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1mo")
        if hist.empty:
            st.warning(f"⚠️ 注意：{ticker} 無數據。")
        return hist
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

    prompt = f"""
    你是一位華爾街資深分析師。今天是 {current_date}。
    請根據以下即時數據與新聞，寫一份簡短的投資日報：
    {market_context}
    
    分析要求：
    1. 必須使用繁體中文。
    2. 禁止將回覆內容包在 ``` (程式碼區塊) 裡面，直接輸出文字。
    3. 直接輸出標題、段落與條列式建議。
    4. 分為『市場情緒』、『個股點評』與『操作建議』三大區塊。
    """

    models_to_try = [
        "models/gemini-3-flash-preview", 
        "models/gemini-2.0-flash",        
        "models/gemini-flash-latest"      
    ]
    
    last_error = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # 成功時處理文字，移除可能誤加的程式碼標籤
            clean_text = response.text.replace("```markdown", "").replace("```text", "").replace("```", "")
            return f"✅ 分析成功 (使用模型: {model_name})\n\n" + clean_text.strip()
        except Exception as e:
            last_error = str(e)
            continue
            
    return f"❌ 所有 AI 模型均忙碌中。\n最後一次錯誤: {last_error}"

# --- 網頁介面 ---
st.set_page_config(page_title="2026 AI 戰情室", layout="wide")
st.title("🛡️ 2026 全球 AI 投資戰情室")
st.caption(f"系統狀態：智慧切換模型 (優先使用 Gemini 3.0 Flash) | {datetime.now().strftime('%Y-%m-%d')}")

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

# 圖表
st.subheader("📊 近 30 天走勢")
if st.session_state.my_watchlist:
    cols = st.columns(2)
    for i, t in enumerate(st.session_state.my_watchlist):
        with cols[i % 2]:
            hist = get_stock_data(t)
            if not hist.empty:
                curr_price = hist['Close'].iloc[-1]
                start_price = hist['Close'].iloc[0]
                roi = ((curr_price - start_price) / start_price) * 100
                st.metric(label=t, value=f"${curr_price:.2f}", delta=f"{roi:.1f}%")
                st.line_chart(hist['Close'])

st.divider()

# AI 分析
st.subheader("🤖 AI 首席策略師分析")
if st.button("🚀 啟動全市場掃描", type="primary"):
    with st.spinner("AI 正在連線 Gemini 3.0 Flash 進行分析..."):
        report = generate_ai_report(st.session_state.my_watchlist)
        if "❌" in report:
            st.error(report)
        else:
            st.success("分析完成！")
            # --- 修正處：正確顯示 report 內容 ---
            st.markdown(report)

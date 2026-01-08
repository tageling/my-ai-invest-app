import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
from datetime import datetime

# 1. API 配置與除錯模式
if "YOUR_GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["YOUR_GEMINI_API_KEY"]
    genai.configure(api_key=api_key.strip())
else:
    st.error("❌ 錯誤：請在 Streamlit Cloud 的 Secrets 中設定 YOUR_GEMINI_API_KEY")
    st.stop()

# 2. 初始化持久化追蹤清單
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["MU", "NVDA", "2408.TW", "SMR", "PLTR"]

# --- 核心數據函數 ---
def get_stock_data(ticker):
    try:
        stock = yf.Ticker(ticker)
        # 抓取 1 個月數據
        hist = stock.history(period="1mo")
        if hist.empty:
            st.warning(f"⚠️ 注意：{ticker} 目前沒有數據，可能是代號錯誤或下市。")
        return hist
    except Exception as e:
        st.error(f"無法抓取 {ticker}: {e}")
        return pd.DataFrame()

# --- 核心 AI 分析函數 (保留最強的 Gemini 3/2.5 切換機制) ---
def generate_ai_report(tickers):
    # 設定目標模型：優先嘗試 Gemini 3 Pro 預覽版
    target_model_name = "models/gemini-3-pro-preview"
    fallback_model_name = "models/gemini-2.5-flash" 
    
    try:
        model = genai.GenerativeModel(target_model_name)
    except:
        # 如果 3.0 失敗，自動切換回 2.5
        model = genai.GenerativeModel(fallback_model_name)

    # 準備數據
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    market_context = f"【報告日期】：{current_date}\n\n"
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            price_data = stock.history(period="1d")
            price = price_data['Close'].iloc[-1] if not price_data.empty else 0
            
            # 抓新聞
            news_list = stock.news
            news_summary = ""
            if news_list:
                for n in news_list[:2]:
                    title = n.get('title') or n.get('summary') or "無標題資訊"
                    news_summary += f"  - {title}\n"
            else:
                news_summary = "  - (無近期新聞)\n"
                
            market_context += f"股票 {t} (現價: ${price:.2f}):\n{news_summary}\n"
            
        except Exception as e:
            market_context += f"股票 {t}: 讀取失敗 ({e})\n"

    # 生成 Prompt
    prompt = f"""
    你是一位華爾街資深分析師。今天是 {current_date}。
    請根據以下即時數據與新聞，寫一份簡短的投資日報：
    
    {market_context}
    
    分析重點：
    1. 市場情緒：目前是貪婪還是恐懼？
    2. 個股點評：針對清單中的股票給出「持有」或「觀望」的建議。
    3. 風險提示：是否有過熱跡象？
    """

    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"❌ AI 分析生成失敗。\n錯誤原因: {str(e)}\n請檢查 API Key 權限。"

# --- 網頁介面 ---
st.set_page_config(page_title="2026 AI 戰情室", layout="wide")
st.title("🛡️ 2026 全球 AI 投資戰情室")
st.caption(f"系統連線正常 (模型自動切換中) | 日期: {datetime.now().strftime('%Y-%m-%d')}")

# 側邊欄
with st.sidebar:
    st.header("📝 追蹤清單")
    new_ticker = st.text_input("輸入代號 (如 NVDA)", placeholder="AAPL")
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

# 主畫面 - 圖表 (改回原版樣式)
st.subheader("📊 近 30 天走勢 (原版圖表)")
if st.session_state.my_watchlist:
    # 這裡改成兩欄排列，讓原版圖表有更多空間顯示日期
    cols = st.columns(2)
    for i, t in enumerate(st.session_state.my_watchlist):
        with cols[i % 2]:
            hist = get_stock_data(t)
            if not hist.empty:
                curr_price = hist['Close'].iloc[-1]
                start_price = hist['Close'].iloc[0]
                roi = ((curr_price - start_price) / start_price) * 100
                
                # 顯示漲跌幅數據
                st.metric(label=t, value=f"${curr_price:.2f}", delta=f"{roi:.1f}%")
                
                # 【改回這行】使用 Streamlit 原生圖表，自動顯示日期與詳細座標
                st.line_chart(hist['Close'])

st.divider()

# 主畫面 - AI 分析
st.subheader("🤖 AI 首席策略師分析")
if st.button("🚀 啟動全市場掃描", type="primary"):
    with st.spinner("AI 正在閱讀全球新聞與財報..."):
        report = generate_ai_report(st.session_state.my_watchlist)
        if "❌" in report:
            st.error(report)
        else:
            st.success("分析完成！")
            st.markdown(report)

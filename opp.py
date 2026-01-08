import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import plotly.graph_objects as go

# 1. API 配置與除錯模式
if "YOUR_GEMINI_API_KEY" in st.secrets:
    api_key = st.secrets["YOUR_GEMINI_API_KEY"]
    # 移除可能存在的空白字符
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

# --- 核心 AI 分析函數 (含自動模型切換) ---
def generate_ai_report(tickers):
    # 步驟 A: 嘗試建立模型 (自動切換機制)
    target_model_name = "models/gemini-1.5-flash" # 首選
    fallback_model_name = "models/gemini-pro"     # 備案
    
    try:
        model = genai.GenerativeModel(target_model_name)
    except:
        st.warning(f"⚠️ 找不到 {target_model_name}，正在切換至舊版模型...")
        model = genai.GenerativeModel(fallback_model_name)

    # 步驟 B: 準備數據
    now = datetime.now()
    current_date = now.strftime("%Y-%m-%d")
    
    market_context = f"【報告日期】：{current_date}\n\n"
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            price_data = stock.history(period="1d")
            price = price_data['Close'].iloc[-1] if not price_data.empty else 0
            
            # 抓新聞 (含防呆機制)
            news_list = stock.news
            news_summary = ""
            if news_list:
                for n in news_list[:2]: # 只看前兩則
                    title = n.get('title') or n.get('summary') or "無標題資訊"
                    news_summary += f"  - {title}\n"
            else:
                news_summary = "  - (無近期新聞)\n"
                
            market_context += f"股票 {t} (現價: ${price:.2f}):\n{news_summary}\n"
            
        except Exception as e:
            market_context += f"股票 {t}: 讀取失敗 ({e})\n"

    # 步驟 C: 生成 Prompt
    prompt = f"""
    你是一位華爾街資深分析師。今天是 {current_date}。
    請根據以下即時數據與新聞，寫一份簡短的投資日報：
    
    {market_context}
    
    分析重點：
    1. 市場情緒：目前是貪婪還是恐懼？
    2. 個股點評：針對清單中的股票給出「持有」或「觀望」的建議。
    3. 風險提示：是否有過熱跡象？
    """

    # 步驟 D: 執行生成 (含詳細錯誤回報)
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # 如果失敗，列出帳號能用的所有模型，方便除錯
        available_models = []
        try:
            for m in genai.list_models():
                if 'generateContent' in m.supported_generation_methods:
                    available_models.append(m.name)
        except:
            available_models = ["無法取得模型清單"]
            
        return f"""
        ❌ AI 分析生成失敗。
        
        錯誤原因: {str(e)}
        
        您的 API Key 目前可用的模型有:
        {available_models}
        
        建議：請將上述錯誤訊息截圖給開發者。
        """

# --- 網頁介面 ---
st.set_page_config(page_title="2026 AI 戰情室", layout="wide")
st.title("🛡️ 2026 全球 AI 投資戰情室")
st.caption(f"系統連線正常 | 日期: {datetime.now().strftime('%Y-%m-%d')}")

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

# 主畫面 - 圖表
st.subheader("📊 近 30 天走勢")
if st.session_state.my_watchlist:
    cols = st.columns(min(len(st.session_state.my_watchlist), 3))
    for i, t in enumerate(st.session_state.my_watchlist):
        with cols[i % 3]:
            hist = get_stock_data(t)
            if not hist.empty:
                curr_price = hist['Close'].iloc[-1]
                start_price = hist['Close'].iloc[0]
                roi = ((curr_price - start_price) / start_price) * 100
                
                st.metric(label=t, value=f"${curr_price:.2f}", delta=f"{roi:.1f}%")
                
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', line=dict(color='#00CC96')))
                fig.update_layout(height=150, margin=dict(l=0, r=0, t=0, b=0), xaxis_visible=False, yaxis_visible=False)
                st.plotly_chart(fig, use_container_width=True)

st.divider()

# 主畫面 - AI 分析
st.subheader("🤖 AI 首席策略師分析")
if st.button("🚀 啟動全市場掃描", type="primary"):
    with st.spinner("AI 正在閱讀全球新聞與財報... (若第一次執行需等待約 10 秒)"):
        report = generate_ai_report(st.session_state.my_watchlist)
        if "❌" in report:
            st.error(report) # 顯示紅色的詳細錯誤
        else:
            st.success("分析完成！")
            st.markdown(report)

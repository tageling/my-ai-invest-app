#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import yfinance as yf
import google.generativeai as genai
import pandas as pd
from datetime import datetime, timedelta
import plotly.graph_objects as go


# 1. API 配置 (請在此填入你的 Gemini API Key)
genai.configure(api_key="AIzaSyCSBRWUE8tpv3zcwzGT7yeIhAbE9Y1yLr8")

# 2. 初始化持久化追蹤清單 (Session State)
if 'my_watchlist' not in st.session_state:
    st.session_state.my_watchlist = ["MU", "NVDA", "2408.TW", "SMR", "PLTR"]

# --- 核心數據與分析函數 ---
def get_stock_data(ticker):
    try:
        # 直接初始化 Ticker，不要傳入 session
        stock = yf.Ticker(ticker)
        # 抓取 1 個月數據
        hist = stock.history(period="1mo")
        
        if hist.empty:
            st.warning(f"注意：{ticker} 目前沒有回傳數據。")
            
        return hist
    except Exception as e:
        st.error(f"抓取 {ticker} 發生錯誤: {e}")
        return pd.DataFrame()

def generate_ai_report(tickers):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 動態獲取今日日期
    now = datetime.now()
    current_date = now.strftime("%Y 年 %m 月 %d 日")
    
    # 彙整清單新聞與行情
    market_context = f"【今日日期】：{current_date}\n\n"
    for t in tickers:
        stock = yf.Ticker(t)
        # 抓取新聞並加入保險機制
        news = stock.news
        price_data = stock.history(period="1d")
        price = price_data['Close'].iloc[-1] if not price_data.empty else 0
        
        market_context += f"--- {t} (現價: ${price:.2f}) ---\n"
        
        if news:
            # 只取前 2 則，並確認有標題才加入
            for n in news[:2]:
                # 修正處：使用 get('title') 避免 KeyError，若無標題則顯示「無標題」
                title = n.get('title') or n.get('summary') or "相關市場變動"
                market_context += f"- 新聞: {title}\n"
        else:
            market_context += "- 目前無即時新聞\n"
    
    # 動態 Prompt
    prompt = f"""
    你是一位資深全球投資策略師。今天是 {current_date}。
    
    請針對目前的即時行情與以下新聞，進行『全方位投資診斷』：
    {market_context}
    
    分析要求：
    1. 必須考慮今日日期所屬的週期。
    2. 指出目前的「市場熱度」是否過熱。
    3. 給出具體的「操作建議」。
    """
    return model.generate_content(prompt).text

# --- 網頁介面設計 ---
st.set_page_config(page_title="2026 AI 投資戰情室", layout="wide")

# 標題與日期
st.title("🛡️ 2026 全球 AI 投資自動化儀表板")
st.markdown(f"**今日日期：** {datetime.now().strftime('%Y-%m-%d %A')}")

# 第一部分：自定義清單管理
with st.sidebar:
    st.header("⚙️ 追蹤清單管理")
    new_ticker = st.text_input("新增代號 (例: AAPL, 2330.TW)", placeholder="輸入代號...")
    if st.button("➕ 新增到追蹤"):
        if new_ticker.upper() not in st.session_state.my_watchlist:
            st.session_state.my_watchlist.append(new_ticker.upper())
            st.rerun()
    
    st.subheader("目前清單")
    for t in st.session_state.my_watchlist:
        col1, col2 = st.columns([4, 1])
        col1.write(t)
        if col2.button("🗑️", key=f"del_{t}"):
            st.session_state.my_watchlist.remove(t)
            st.rerun()

# 第二部分：即時行情與圖表
st.header("📈 即時趨勢監控 (近 30 天)")
cols = st.columns(min(len(st.session_state.my_watchlist), 3))
for i, t in enumerate(st.session_state.my_watchlist):
    col_idx = i % 3
    hist = get_stock_data(t)
    if not hist.empty:
        with cols[col_idx]:
            # 計算漲跌
            change = ((hist['Close'].iloc[-1] / hist['Close'].iloc[0]) - 1) * 100
            st.metric(t, f"${hist['Close'].iloc[-1]:.2f}", f"{change:.2f}% (1mo)")
            
            # 繪製 Plotly 線圖
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=hist.index, y=hist['Close'], mode='lines', name=t))
            fig.update_layout(height=200, margin=dict(l=0, r=0, t=0, b=0), showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

st.divider()

# 第三部分：AI 深度診斷
st.header("🧠 AI 首席策略師：當日分析報告")
if st.button("🚀 啟動全市場 AI 掃描"):
    with st.spinner('AI 正在抓取全球最新新聞並進行深度診斷...'):
        report = generate_ai_report(st.session_state.my_watchlist)
        st.success("分析報告已生成")
        st.markdown(report)

st.divider()
st.caption("數據來源：Yahoo Finance | AI 分析：Gemini 3 Flash | 本程式由 AI 與投資夥伴共同開發")


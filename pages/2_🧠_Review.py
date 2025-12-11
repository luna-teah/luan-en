import streamlit as st
import utils
import time
import random

# --- 页面配置 ---
st.set_page_config(page_title="智能复习", page_icon="🧠", layout="wide")
utils.local_css() # 调用工具箱里的CSS

# --- 检查登录 ---
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先在主页登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

# --- 侧边栏 ---
with st.sidebar:
    if st.button("⬅️ 返回主页"):
        st.switch_page("app_v6.py")
    st.divider()
    st.write(f"当前用户: **{user}**")

st.title("🧠 智能复习")

# --- 核心逻辑 ---
# 1. 获取用户进度
u_doc = db.users.find_one({"_id": user})
prog = u_doc.get("progress", {})

# 2. 筛选今天需要复习的词 (Next Review Time < Now)
now = time.time()
due_words = [w for w, info in prog.items() if info['next_review'] < now]

# 3. 复习流程
if not due_words:
    st.balloons()
    st.success("🎉 太棒了！今日复习任务已清空！")
    st.info("💡 快去 '⚡ 学习新词' 或 '🚀 智能扩词' 添加新任务吧！")
else:
    # 随机抽取一个词 (使用 session_state 防止刷新变词)
    if 'curr_w' not in st.session_state or st.session_state['curr_w'] not in due_words:
        st.session_state['curr_w'] = random.choice(due_words)
        st.session_state['show_ans'] = False # 默认遮挡答案
    
    w = st.session_state['curr_w']
    
    # 从公共库获取单词详情
    d = db.library.find_one({"word": w}) or {}
    
    # --- 卡片显示 ---
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#1F2937; font-size:4rem; margin-bottom:10px;">{w}</h1>
        <p style="color:#666; font-style:italic;">/{d.get('phonetic','...')}/</p>
    </div>
    """, unsafe_allow_html=True)
    
    # 播放按钮
    c_audio, c_blank = st.columns([1, 10])
    with c_audio:
        if st.button("🔊 播放"): utils.play_audio(w)
    
    st.markdown("---")

    # --- 交互区域 ---
    if not st.session_state['show_ans']:
        # 遮挡状态
        if st.button("👁️ 查看答案", type="primary", use_container_width=True):
            st.session_state['show_ans'] = True
            st.rerun()
    else:
        # 揭晓状态
        st.markdown(f"""
        <div class="meaning-box">
            <div style="font-size:0.8rem; color:#065F46;">MEANING</div>
            <div class="meaning-text">{d.get('meaning')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if d.get('mnemonic'):
            st.markdown(f"""
            <div class="brain-box">
                <div style="font-size:0.8rem; color:#4338CA;">🧠 MEMORY TRICK</div>
                <div class="brain-text">{d['mnemonic']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.markdown("#### 你记得怎么样？")
        
        c1, c2, c3 = st.columns(3)
        lvl = prog[w]['level']
        
        with c1:
            if st.button("🔴 忘了", use_container_width=True):
                # 忘了 -> 重置等级为0 (立即复习)
                db.users.update_one(
                    {"_id": user}, 
                    {"$set": {f"progress.{w}": {"level": 0, "next_review": utils.get_next_time(0)}}}
                )
                st.session_state['show_ans'] = False
                del st.session_state['curr_w']
                st.rerun()
                
        with c2:
            if st.button("🟢 记得", use_container_width=True):
                # 记得 -> 等级+1
                db.users.update_one(
                    {"_id": user}, 
                    {"$set": {f"progress.{w}": {"level": lvl+1, "next_review": utils.get_next_time(lvl+1)}}}
                )
                st.session_state['show_ans'] = False
                del st.session_state['curr_w']
                st.rerun()
                
        with c3:
            if st.button("🚀 太简单", use_container_width=True):
                # 太简单 -> 等级+2 (跳级)
                db.users.update_one(
                    {"_id": user}, 
                    {"$set": {f"progress.{w}": {"level": lvl+2, "next_review": utils.get_next_time(lvl+2)}}}
                )
                st.session_state['show_ans'] = False
                del st.session_state['curr_w']
                st.rerun()

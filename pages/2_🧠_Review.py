import streamlit as st
import utils
import time
import random

st.set_page_config(page_title="智能复习", page_icon="🧠", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

with st.sidebar:
    if st.button("⬅️ 回到主页"): st.switch_page("app_v6.py")

# 获取复习任务
u_doc = db.users.find_one({"_id": user})
prog = u_doc.get("progress", {})
now = time.time()
due_words = [w for w, i in prog.items() if i['next_review'] < now]

st.markdown("## 🧠 智能复习")

if not due_words:
    st.balloons()
    st.info("太棒了！今天的复习任务全部完成了！")
else:
    # 随机取词
    if 'curr_w' not in st.session_state or st.session_state['curr_w'] not in due_words:
        st.session_state['curr_w'] = random.choice(due_words)
        st.session_state['show_ans'] = False
    
    w = st.session_state['curr_w']
    d = db.library.find_one({"word": w}) or {}
    
    # 单词卡 (遮挡模式)
    st.markdown(f"""
    <div style="text-align:center; padding:50px; background:white; border-radius:20px; box-shadow:0 5px 15px rgba(0,0,0,0.05);">
        <h1 style="font-size:4rem; color:#1F2937;">{w}</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    if not st.session_state['show_ans']:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            if st.button("👁️ 查看答案", type="primary", use_container_width=True):
                st.session_state['show_ans'] = True
                st.rerun()
    else:
        # 显示答案
        st.markdown(f"""
        <div class="meaning-box" style="text-align:center;">
            <div class="meaning-text">{d.get('meaning')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if d.get('mnemonic'):
            st.info(f"🧠 {d['mnemonic']}")
            
        st.markdown("#### 你记得怎么样？")
        c1, c2, c3 = st.columns(3)
        lvl = prog[w]['level']
        
        with c1:
            if st.button("🔴 忘了", use_container_width=True):
                db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": 0, "next_review": utils.get_next_time(0)}}})
                st.session_state['show_ans']=False; del st.session_state['curr_w']; st.rerun()
        with c2:
            if st.button("🟢 记得", use_container_width=True):
                db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": lvl+1, "next_review": utils.get_next_time(lvl+1)}}})
                st.session_state['show_ans']=False; del st.session_state['curr_w']; st.rerun()

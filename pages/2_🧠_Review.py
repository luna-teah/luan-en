import streamlit as st
import utils
import time
import random

st.set_page_config(page_title="复习", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.stop()

user = st.session_state['username']
db = utils.get_db()

if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")
st.title("🧠 智能复习")

u_doc = db.users.find_one({"_id": user})
prog = u_doc.get("progress", {})
due = [w for w, i in prog.items() if i['next_review'] < time.time()]

if not due:
    st.balloons()
    st.success("今日任务清空！")
else:
    if 'curr_w' not in st.session_state or st.session_state['curr_w'] not in due:
        st.session_state['curr_w'] = random.choice(due)
        st.session_state['show_ans'] = False
        
    w = st.session_state['curr_w']
    d = utils.smart_fetch(w) or {} # 重新获取以确保有新字段
    
    st.markdown(f"""<div class="word-card"><h1 style="color:#4F46E5;font-size:4rem;">{w}</h1></div>""", unsafe_allow_html=True)
    
    if not st.session_state['show_ans']:
        if st.button("👁️ 看答案", type="primary", use_container_width=True):
            st.session_state['show_ans'] = True
            st.rerun()
    else:
        # 显示详细信息
        c1, c2 = st.columns(2)
        with c1:
            st.info(f"📚 {d.get('meaning')}")
            if d.get('roots'): st.warning(f"🌱 词根: {d['roots']}")
        with c2:
            if d.get('collocations'): 
                cols = ", ".join(d['collocations'][:3])
                st.success(f"🔗 搭配: {cols}")
            if d.get('mnemonic'): st.error(f"🧠 {d['mnemonic']}")
            
        st.markdown("---")
        c1, c2, c3 = st.columns(3)
        lvl = prog[w]['level']
        with c1:
            if st.button("🔴 忘了"):
                db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": 0, "next_review": utils.get_next_time(0)}}})
                st.session_state['show_ans']=False; del st.session_state['curr_w']; st.rerun()
        with c2:
            if st.button("🟢 记得"):
                db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": lvl+1, "next_review": utils.get_next_time(lvl+1)}}})
                st.session_state['show_ans']=False; del st.session_state['curr_w']; st.rerun()
        with c3:
            if st.button("🚀 太简单"):
                db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": lvl+2, "next_review": utils.get_next_time(lvl+2)}}})
                st.session_state['show_ans']=False; del st.session_state['curr_w']; st.rerun()

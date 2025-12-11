import streamlit as st
import utils

st.set_page_config(page_title="学习新词", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先在主页登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

st.title("⚡ 学习新词")
if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")

# 逻辑
all_words = list(db.library.find({}))
u_prog = db.users.find_one({"_id": user}).get('progress', {})
cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        c = w.get('category', '未分类')
        cats[c] = cats.get(c, 0) + 1

options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("选择分类", options)

target_cat = sel.split(" (")[0]
pool = [w for w in all_words if w['word'] not in u_prog and (target_cat == "全部" or w.get('category') == target_cat)]

if not pool:
    st.success("🎉 该分类学完了！")
else:
    w_data = pool[0]
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#4F46E5; font-size:3.5rem;">{w_data['word']}</h1>
        <p style="color:#666; font-style:italic;">/{w_data.get('phonetic','...')}/</p>
        <div class="info-box"><b>MEANING:</b> {w_data.get('meaning')}</div>
        {'<div class="brain-box"><b>🧠 脑洞:</b> '+w_data['mnemonic']+'</div>' if w_data.get('mnemonic') else ''}
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("🔊 播放"): utils.play_audio(w_data['word'])
    with c2:
        if st.button("✅ 学会了", type="primary", use_container_width=True):
            db.users.update_one({"_id": user}, {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
            st.rerun()
            
    st.markdown("---")
    for s in w_data.get('sentences', []):
        st.markdown(f"**{s['en']}**\n\n*{s['cn']}*")
        st.divider()

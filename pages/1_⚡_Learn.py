import streamlit as st
import utils

st.set_page_config(page_title="学习", layout="wide")

# 侧边栏调色板
with st.sidebar:
    st.markdown("### 🎨 界面设置")
    user_color = st.color_picker("字体颜色", "#1F2937")
    utils.set_style(text_color=user_color)

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.stop()

user = st.session_state['username']
db = utils.get_db()

if st.button("⬅️ 主页"): st.switch_page("app_v6.py")
st.title("⚡ 学习新词")

all_words = list(db.library.find({}))
cats = list(set([w.get('category','未分类') for w in all_words]))
u_prog = db.users.find_one({"_id": user}).get('progress', {})

options = ["全部"] + [c for c in cats]
sel = st.selectbox("📂 选择分类", options)

pool = [w for w in all_words if w['word'] not in u_prog and (sel=="全部" or w.get('category')==sel)]

if not pool:
    st.success("🎉 本分类已学完！")
else:
    w = pool[0]
    
    # === 单词主卡 ===
    st.markdown(f"""<div class="word-card"><h1 style="color:#4F46E5;font-size:4rem;margin:0;">{w['word']}</h1><p style="font-size:1.5rem;font-style:italic;color:#666;">/{w.get('phonetic','...')}/</p></div>""", unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        # 1. 含义
        st.markdown(f"""<div class="info-container box-meaning"><span class="label-head">📚 含义 (MEANING)</span>{w.get('meaning')}</div>""", unsafe_allow_html=True)
        # 2. 词根
        if w.get('roots'):
            st.markdown(f"""<div class="info-container box-roots"><span class="label-head">🌱 词根 (ROOTS)</span>{w['roots']}</div>""", unsafe_allow_html=True)
            
    with c2:
        # 3. 英文搭配 (自动转列表)
        if w.get('collocations'):
            cols = "".join([f"<li>{c}</li>" for c in w['collocations']])
            st.markdown(f"""<div class="info-container box-colloc"><span class="label-head">🔗 英文搭配 (PHRASES)</span><ul>{cols}</ul></div>""", unsafe_allow_html=True)
        # 4. 脑洞
        if w.get('mnemonic'):
            st.markdown(f"""<div class="info-container box-mnem"><span class="label-head">🧠 记忆法 (TRICK)</span>{w['mnemonic']}</div>""", unsafe_allow_html=True)

    st.markdown("---")
    
    # 5. 造句
    st.markdown("#### 📖 场景造句")
    if w.get('sentences'):
        for s in w['sentences']:
            st.markdown(f"**{s.get('en')}**")
            st.caption(f"{s.get('cn')}")
            st.divider()
    
    # 底部按钮
    b1, b2 = st.columns([1, 4])
    with b1:
        if st.button("🔊 播放"): utils.play_audio(w['word'])
    with b2:
        if st.button("✅ 我学会了 (下一个)", type="primary", use_container_width=True):
            db.users.update_one({"_id": user}, {"$set": {f"progress.{w['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
            st.rerun()

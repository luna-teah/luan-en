import streamlit as st
import utils

st.set_page_config(page_title="学习", layout="wide")
utils.local_css() # 确保这里也加载了样式

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")
st.title("⚡ 学习新词")

all_words = list(db.library.find({}))
cats = list(set([w.get('category','未分类') for w in all_words]))
u_prog = db.users.find_one({"_id": user}).get('progress', {})

# 修复下拉菜单显示
options = ["全部"] + [c for c in cats]
sel = st.selectbox("📂 选择分类", options)

pool = [w for w in all_words if w['word'] not in u_prog and (sel=="全部" or w.get('category')==sel)]

if not pool:
    st.success("🎉 本分类已学完！")
else:
    # 强制更新数据（如果旧数据没有词根，就重新查一次AI）
    w_raw = pool[0]
    w = utils.smart_fetch(w_raw['word']) # 这步会自动补全词根和搭配
    if not w: w = w_raw # 兜底

    # === 卡片显示 ===
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#4F46E5 !important; font-size:4rem; margin:0;">{w['word']}</h1>
        <p style="color:#6B7280 !important; font-size:1.5rem; font-style:italic;">/{w.get('phonetic','...')}/</p>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"""
        <div class="meaning-box">
            <div style="font-weight:bold; opacity:0.7;">📚 MEANING</div>
            <div style="font-size:1.2rem; font-weight:bold;">{w.get('meaning')}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if w.get('roots'):
            st.markdown(f"""
            <div class="roots-box">
                <div style="font-weight:bold; opacity:0.7;">🌱 ROOTS (词根)</div>
                <div>{w['roots']}</div>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        if w.get('collocations'):
            # 把数组转成 HTML 列表
            cols = "".join([f"<li>{c}</li>" for c in w['collocations']])
            st.markdown(f"""
            <div class="meaning-box" style="background:#F0F9FF !important; border-left:5px solid #0EA5E9 !important; color:#0C4A6E !important;">
                <div style="font-weight:bold; opacity:0.7;">🔗 PHRASES (英文搭配)</div>
                <ul style="margin:0; padding-left:20px;">{cols}</ul>
            </div>
            """, unsafe_allow_html=True)
            
        if w.get('mnemonic'):
            st.markdown(f"""
            <div class="brain-box">
                <div style="font-weight:bold; opacity:0.7;">🧠 TRICK (脑洞)</div>
                <div>{w['mnemonic']}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### 📖 场景造句")
    if w.get('sentences'):
        for s in w['sentences']:
            st.markdown(f"**{s.get('en')}**")
            st.caption(f"{s.get('cn')}")
            st.divider()
    
    c_a, c_b = st.columns([1,4])
    with c_a:
        if st.button("🔊 播放"): utils.play_audio(w['word'])
    with c_b:
        if st.button("✅ 我学会了 (Next)", type="primary", use_container_width=True):
            db.users.update_one({"_id": user}, {"$set": {f"progress.{w['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
            st.rerun()

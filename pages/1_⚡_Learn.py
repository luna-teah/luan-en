import streamlit as st
import utils

st.set_page_config(page_title="学习", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")
st.title("⚡ 学习新词")

all_words = list(db.library.find({}))
u_prog = db.users.find_one({"_id": user}).get('progress', {})

# 分类去重
cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        raw_cat = str(w.get('category', '未分类')).strip()
        cats[raw_cat] = cats.get(raw_cat, 0) + 1

options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("📂 选择分类", options)

target_cat = sel.split(" (")[0] if "(" in sel else sel

pool = []
for w in all_words:
    if w['word'] not in u_prog:
        w_cat = str(w.get('category', '未分类')).strip()
        if target_cat == "全部" or w_cat == target_cat:
            pool.append(w)

if not pool:
    st.success("🎉 本分类已学完！")
else:
    # 强制刷新旧词
    w_raw = pool[0]
    if not w_raw.get('sentences') or len(w_raw.get('sentences')) < 3:
        w = utils.smart_fetch(w_raw['word']) or w_raw
    else:
        w = w_raw

    # === 卡片显示 (无缩进，防止乱码) ===
    st.markdown(f"""
<div class="word-card">
    <h1 style="color:#4F46E5 !important; font-size:4rem; margin:0;">{w['word']}</h1>
    <p style="color:#6B7280 !important; font-size:1.5rem; font-style:italic;">/{w.get('phonetic','...')}/</p>
    <span class="tag-pill">{str(w.get('category','')).strip()}</span>
</div>
""", unsafe_allow_html=True)
    
    # 播放按钮
    c_audio, c_space = st.columns([2, 8])
    with c_audio:
        if st.button("🔊 播放发音", use_container_width=True): 
            utils.play_audio(w['word'])

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
    <div style="color:#C2410C;">{w['roots']}</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        if w.get('collocations'):
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
    st.markdown("#### 📖 阶梯例句 (由简入难)")
    
    labels = ["🌱 简单 (Simple)", "⛅ 日常 (Daily)", "💼 商务 (Business)"]
    
    if w.get('sentences'):
        for i, s in enumerate(w['sentences']):
            label = labels[i] if i < 3 else "📝 例句"
            # 布局：左边文字，右边按钮
            c_txt, c_btn = st.columns([8, 2])
            with c_txt:
                st.markdown(f"""
<div style="background:white; border-left: 4px solid #E5E7EB; padding: 10px 15px; margin-bottom: 10px;">
    <div style="font-size:0.8rem; color:#9CA3AF; font-weight:bold; margin-bottom:4px;">{label}</div>
    <div style="font-size:1.1rem; color:#1F2937; margin-bottom:2px;">{s.get('en')}</div>
    <div style="font-size:0.9rem; color:#6B7280;">{s.get('cn')}</div>
</div>
""", unsafe_allow_html=True)
            with c_btn:
                st.write("")
                st.write("")
                if st.button("🔈", key=f"s_btn_{i}"):
                    utils.play_audio(s.get('en'))
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("✅ 我学会了 (Next)", type="primary", use_container_width=True):
        db.users.update_one({"_id": user}, {"$set": {f"progress.{w['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
        st.rerun()

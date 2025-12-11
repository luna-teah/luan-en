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

# === 🧠 智能分类清洗 (解决 Business 和 Business 重复问题) ===
cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        # 强制转字符串并去除空格
        raw_cat = str(w.get('category', '未分类')).strip()
        cats[raw_cat] = cats.get(raw_cat, 0) + 1

options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("📂 选择分类", options)

target_cat = sel.split(" (")[0] if "(" in sel else sel

# === 筛选词库 ===
pool = []
for w in all_words:
    if w['word'] not in u_prog:
        w_cat = str(w.get('category', '未分类')).strip()
        if target_cat == "全部" or w_cat == target_cat:
            pool.append(w)

if not pool:
    st.success("🎉 本分类已学完！")
else:
    w_raw = pool[0]
    w = utils.smart_fetch(w_raw['word']) 
    if not w: w = w_raw 

    # === 🔥 调整布局：播放按钮在最上面 ===
    c_audio, c_space = st.columns([2, 8])
    with c_audio:
        # 按钮放在这里！
        if st.button("🔊 播放发音", use_container_width=True): 
            utils.play_audio(w['word'])

    # === 单词卡片 ===
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#4F46E5 !important; font-size:4rem; margin:0;">{w['word']}</h1>
        <p style="color:#6B7280 !important; font-size:1.5rem; font-style:italic;">/{w.get('phonetic','...')}/</p>
        <span class="tag-pill">{str(w.get('category','')).strip()}</span>
    </div>
    """, unsafe_allow_html=True)
    
    # === 详情内容 ===
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
            <div class="word-card" style="padding:15px; margin-top:15px; text-align:left; background:#FFF7ED !important; border:1px solid #FFEDD5;">
                <div style="font-weight:bold; opacity:0.7; color:#C2410C;">🌱 ROOTS (词根)</div>
                <div style="color:#9A3412;">{w['roots']}</div>
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
    st.markdown("#### 📖 场景造句")
    if w.get('sentences'):
        for s in w['sentences']:
            st.markdown(f"**{s.get('en')}**")
            st.caption(f"{s.get('cn')}")
            st.divider()
    
    # 底部只留“学会了”按钮
    if st.button("✅ 我学会了 (Next)", type="primary", use_container_width=True):
        db.users.update_one({"_id": user}, {"$set": {f"progress.{w['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
        st.rerun()

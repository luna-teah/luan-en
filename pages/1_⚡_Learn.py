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

# === 🧠 智能分类清洗逻辑 ===
cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        # 1. 获取分类，默认'未分类'
        raw_cat = w.get('category', '未分类')
        # 2. 强制转字符串 + 去除首尾空格 (解决 'Business ' 重复问题)
        clean_cat = str(raw_cat).strip()
        # 3. 统计
        cats[clean_cat] = cats.get(clean_cat, 0) + 1

# 生成选项
options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("📂 选择分类", options)

# 获取用户选择的纯分类名 (去掉括号里的数字)
target_cat = sel.split(" (")[0] if "(" in sel else sel

# === 筛选词库 ===
pool = []
for w in all_words:
    if w['word'] not in u_prog:
        # 这里也要清洗一下再比对
        w_cat = str(w.get('category', '未分类')).strip()
        
        if target_cat == "全部" or w_cat == target_cat:
            pool.append(w)

if not pool:
    st.success("🎉 本分类已学完！")
else:
    # 强制更新数据（如果旧数据没有词根，就重新查一次AI）
    w_raw = pool[0]
    w = utils.smart_fetch(w_raw['word']) 
    if not w: w = w_raw 

    # === 卡片显示 ===
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#4F46E5 !important; font-size:4rem; margin:0;">{w['word']}</h1>
        <p style="color:#6B7280 !important; font-size:1.5rem; font-style:italic;">/{w.get('phonetic','...')}/</p>
        <span class="tag-pill">{str(w.get('category','')).strip()}</span>
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
    
    c_a, c_b = st.columns([1,4])
    with c_a:
        if st.button("🔊 播放"): utils.play_audio(w['word'])
    with c_b:
        if st.button("✅ 我学会了 (Next)", type="primary", use_container_width=True):
            db.users.update_one({"_id": user}, {"$set": {f"progress.{w['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
            st.rerun()

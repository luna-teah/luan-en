import streamlit as st
import utils

st.set_page_config(page_title="学习新词", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先在主页登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

c_back, c_title = st.columns([1, 8])
with c_back:
    if st.button("⬅️ 主页"): st.switch_page("app_v6.py")
with c_title:
    st.title("⚡ 学习新词")

# 数据获取与筛选
all_words = list(db.library.find({}))
u_prog = db.users.find_one({"_id": user}).get('progress', {})

cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        c = w.get('category', '未分类')
        cats[c] = cats.get(c, 0) + 1

# 修复：确保下拉菜单选项是字符串，防止看不见
options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("📂 选择分类 (筛选已生效)", options)

target_cat = sel.split(" (")[0]
pool = [w for w in all_words if w['word'] not in u_prog and (target_cat == "全部" or w.get('category') == target_cat)]

if not pool:
    st.success("🎉 该分类已学完！")
else:
    w_data = pool[0]
    
    # === 单词主卡 ===
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#4F46E5; font-size:4rem; margin:0;">{w_data['word']}</h1>
        <p style="color:#6B7280; font-style:italic; font-size:1.5rem;">/{w_data.get('phonetic','...')}/</p>
    </div>
    """, unsafe_allow_html=True)
    
    # === 详情模块 (新版布局) ===
    c1, c2 = st.columns([1, 1])
    
    with c1:
        # 1. 含义
        st.markdown(f"""
        <div class="section-box box-meaning">
            <span class="label-title">📚 MEANING (含义)</span>
            {w_data.get('meaning')}
        </div>
        """, unsafe_allow_html=True)
        
        # 2. 词根 (新功能)
        if w_data.get('roots'):
            st.markdown(f"""
            <div class="section-box box-roots">
                <span class="label-title">🌱 ROOTS (词根词源)</span>
                {w_data['roots']}
            </div>
            """, unsafe_allow_html=True)

    with c2:
        # 3. 英文搭配 (新功能)
        if w_data.get('collocations'):
            # 把数组转成点状列表
            collocs_html = "".join([f"<li>{c}</li>" for c in w_data['collocations']])
            st.markdown(f"""
            <div class="section-box box-colloc">
                <span class="label-title">🔗 COLLOCATIONS (地道搭配)</span>
                <ul style="margin:0; padding-left:20px;">{collocs_html}</ul>
            </div>
            """, unsafe_allow_html=True)
            
        # 4. 脑洞
        if w_data.get('mnemonic'):
            st.markdown(f"""
            <div class="section-box box-mnem">
                <span class="label-title">🧠 MEMORY TRICK (脑洞)</span>
                {w_data['mnemonic']}
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    
    # === 5. 场景例句 (完整展示) ===
    st.markdown("#### 📖 场景例句")
    if w_data.get('sentences'):
        for s in w_data['sentences']:
            st.markdown(f"""
            <div style="background:white; padding:10px; border-radius:8px; margin-bottom:8px; border:1px solid #eee;">
                <div style="color:#1F2937; font-weight:bold;">{s.get('en')}</div>
                <div style="color:#6B7280; font-size:0.9rem;">{s.get('cn')}</div>
            </div>
            """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # 底部操作栏
    b1, b2 = st.columns([1, 4])
    with b1:
        if st.button("🔊 播放"): utils.play_audio(w_data['word'])
    with b2:
        if st.button("✅ 我学会了 (Next)", type="primary", use_container_width=True):
            db.users.update_one(
                {"_id": user},
                {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}}
            )
            st.rerun()

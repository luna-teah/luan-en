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

# 获取数据
all_words = list(db.library.find({}))
u_prog = db.users.find_one({"_id": user}).get('progress', {})

# 分类统计
cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        c = w.get('category', '未分类')
        cats[c] = cats.get(c, 0) + 1

options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("选择分类", options)

# 筛选
target_cat = sel.split(" (")[0]
pool = [w for w in all_words if w['word'] not in u_prog and (target_cat == "全部" or w.get('category') == target_cat)]

if not pool:
    st.success("🎉 该分类学完了！")
else:
    w_data = pool[0]
    
    # --- 卡片显示 ---
    # 注意：这里必须用 unsafe_allow_html=True 才能让 HTML 生效，否则就会显示乱码
    st.markdown(f"""
    <div class="word-card">
        <h1 style="color:#4F46E5; font-size:3.5rem; margin:0;">{w_data['word']}</h1>
        <p style="color:#666; font-style:italic;">/{w_data.get('phonetic','...')}/</p>
        
        <div style="background:#ECFDF5; padding:15px; border-radius:8px; margin-top:15px; text-align:left;">
            <div style="color:#065F46; font-weight:bold; font-size:0.8rem;">MEANING</div>
            <div style="color:#065F46; font-size:1.2rem; font-weight:bold;">{w_data.get('meaning')}</div>
        </div>
        
        {'<div style="background:#EEF2FF; padding:15px; border-radius:8px; margin-top:10px; text-align:left;"><div style="color:#4338CA; font-weight:bold;">🧠 脑洞</div><div style="color:#4338CA;">'+w_data['mnemonic']+'</div></div>' if w_data.get('mnemonic') else ''}
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("🔊 播放"): utils.play_audio(w_data['word'])
    with c2:
        if st.button("✅ 我学会了", type="primary", use_container_width=True):
            db.users.update_one(
                {"_id": user},
                {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}}
            )
            st.rerun()
            
    st.markdown("---")
    # 例句 (直接显示，不用HTML，防止出错)
    st.markdown("### 📚 场景例句")
    for s in w_data.get('sentences', []):
        st.markdown(f"**{s.get('en')}**")
        st.caption(f"{s.get('cn')}")
        st.divider()

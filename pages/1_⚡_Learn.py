import streamlit as st
import utils # 导入刚才写的工具箱

st.set_page_config(page_title="学习新词", page_icon="⚡", layout="wide")
utils.local_css()

# 检查登录
if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先在主页登录")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

st.markdown("## ⚡ 学习新词")

# --- 侧边栏：分类选择 ---
with st.sidebar:
    if st.button("⬅️ 回到主页"): st.switch_page("app_v6.py")
    st.divider()
    
    # 统计分类
    all_words = list(db.library.find({}))
    u_prog = db.users.find_one({"_id": user}).get('progress', {})
    
    cats = {}
    for w in all_words:
        if w['word'] not in u_prog: # 只算没学的
            c = w.get('category', '未分类')
            cats[c] = cats.get(c, 0) + 1
            
    # 下拉菜单
    options = ["全部"] + [f"{k} ({v})" for k,v in cats.items()]
    sel = st.selectbox("选择分类", options)

# --- 主界面 ---
pool = []
target_cat = sel.split(" (")[0] if "(" in sel else sel

for w in all_words:
    if w['word'] not in u_prog:
        if target_cat == "全部" or w.get('category') == target_cat:
            pool.append(w)

if not pool:
    st.success("🎉 这个分类学完了！快去 [智能扩词] 页面生成新词吧。")
else:
    # 进度条
    st.progress((len(all_words) - len(pool)) / len(all_words) if all_words else 0)
    st.caption(f"剩余待学: {len(pool)} 个")
    
    w_data = pool[0] # 取第一个
    
    # === 渲染卡片 (这里是关键，解决了代码乱码问题) ===
    st.markdown(f"""
    <div class="word-card">
        <div class="big-word">{w_data['word']}</div>
        <div style="color:#666; font-style:italic; margin-bottom:10px;">/{w_data.get('phonetic','...')}/</div>
        <div style="background:#E0E7FF; color:#4338CA; display:inline-block; padding:2px 10px; border-radius:10px; font-size:0.8rem;">
            {w_data.get('category','General')}
        </div>
        
        <div class="meaning-box">
            <div style="font-size:0.8rem; color:#065F46;">MEANING</div>
            <div class="meaning-text">{w_data.get('meaning')}</div>
        </div>
        
        {'<div class="brain-box"><div style="font-size:0.8rem; color:#4338CA;">🧠 MEMORY TRICK</div><div class="brain-text">'+w_data['mnemonic']+'</div></div>' if w_data.get('mnemonic') else ''}
    </div>
    """, unsafe_allow_html=True)
    
    # 按钮区
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        if st.button("🔊 播放发音", use_container_width=True):
            utils.play_audio(w_data['word'])
        
        st.markdown("---")
        
        # 例句展示
        if w_data.get('sentences'):
            for s in w_data['sentences']:
                st.markdown(f"**{s['en']}**")
                st.caption(f"{s['cn']}")
                st.divider()
        
        if st.button("✅ 我学会了", type="primary", use_container_width=True):
            # 存入数据库
            db.users.update_one(
                {"_id": user},
                {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}}
            )
            st.rerun()

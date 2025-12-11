import streamlit as st
import utils
import os

# --- 0. 暴力强制生成配置文件 (解决默认黑夜模式) ---
# 这一步非常关键，它会告诉 Streamlit "必须用亮色主题"
streamlit_config = """
[theme]
base="light"
primaryColor="#4F46E5"
backgroundColor="#F3F4F6"
secondaryBackgroundColor="#FFFFFF"
textColor="#1F2937"
font="sans serif"
"""
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
# 每次运行都覆盖写入，确保配置生效
with open(".streamlit/config.toml", "w") as f:
    f.write(streamlit_config)

# --- 1. 页面初始化 ---
st.set_page_config(page_title="Luna Pro V22", page_icon="💎", layout="wide")
utils.local_css() # 加载纠色 CSS

# --- 2. 登录逻辑 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login_page():
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5 !important'>💎 Luna Pro V22</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab1, tab2 = st.tabs(["登录", "注册"])
        db = utils.get_db()
        with tab1:
            u = st.text_input("用户名", key="l1")
            p = st.text_input("密码", type="password", key="l2")
            if st.button("🚀 登录", use_container_width=True, type="primary"):
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and utils.check_hashes(p, user['password']):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("密码错误")
                else: st.error("数据库未连接")
        with tab2:
            nu = st.text_input("新用户名", key="r1")
            np = st.text_input("设置密码", type="password", key="r2")
            if st.button("✨ 注册", use_container_width=True):
                if db and nu:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}})
                        st.success("注册成功！")
                    else: st.warning("用户已存在")

# --- 3. 导航大厅 ---
if not st.session_state['logged_in']:
    login_page()
else:
    st.markdown(f"## 👋 Hi, {st.session_state['username']}")
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("""
        <div class="nav-card">
            <h3 style="color:#111827 !important">⚡ 学习新词</h3>
            <p style="color:#6B7280 !important">词根 · 搭配 · 场景</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Learn", use_container_width=True, type="secondary"): st.switch_page("pages/1_⚡_Learn.py")
        
    with c2:
        st.markdown("""
        <div class="nav-card">
            <h3 style="color:#111827 !important">🧠 智能复习</h3>
            <p style="color:#6B7280 !important">艾宾浩斯记忆曲线</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Review", use_container_width=True, type="secondary"): st.switch_page("pages/2_🧠_Review.py")
        
    with c3:
        st.markdown("""
        <div class="nav-card">
            <h3 style="color:#111827 !important">🚀 扩充词库</h3>
            <p style="color:#6B7280 !important">AI 批量生成场景词</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Add", use_container_width=True, type="secondary"): st.switch_page("pages/3_🚀_Add.py")
    
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

import streamlit as st
import utils  # 确保这里导入了 utils
import secrets

st.set_page_config(page_title="Luna Pro 主页", page_icon="💎", layout="wide")

# 🔥 关键：一进来就加载纠色样式
utils.local_css()

# --- 登录 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

if not st.session_state['logged_in']:
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5 !important'>💎 Luna Pro V21</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        db = utils.get_db()
        with tab1:
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.button("🚀 登录", use_container_width=True):
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and utils.check_hashes(p, user['password']):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("密码错误")
                else: st.error("数据库未连接")
        with tab2:
            nu = st.text_input("新用户名")
            np = st.text_input("新密码", type="password")
            if st.button("✨ 注册", use_container_width=True):
                if db and nu:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}})
                        st.success("注册成功！")
                    else: st.warning("用户已存在")

# --- 主导航 ---
else:
    st.markdown(f"## 👋 Hi, {st.session_state['username']}")
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("""
        <div class="nav-card">
            <h3 style="color:#111827 !important">⚡ 学习新词</h3>
            <p style="color:#6B7280 !important">分类学习 · 包含词根/搭配</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Learn", use_container_width=True): st.switch_page("pages/1_⚡_Learn.py")
        
    with c2:
        st.markdown("""
        <div class="nav-card">
            <h3 style="color:#111827 !important">🧠 智能复习</h3>
            <p style="color:#6B7280 !important">巩固记忆 · 艾宾浩斯</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Review", use_container_width=True): st.switch_page("pages/2_🧠_Review.py")
        
    with c3:
        st.markdown("""
        <div class="nav-card">
            <h3 style="color:#111827 !important">🚀 扩充词库</h3>
            <p style="color:#6B7280 !important">AI 批量生成 · 场景词汇</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Add", use_container_width=True): st.switch_page("pages/3_🚀_Add.py")
            
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

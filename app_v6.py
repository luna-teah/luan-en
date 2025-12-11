import streamlit as st
import utils  # ✅ 必须导入这个工具箱！
import secrets

# --- 0. 全局配置 ---
st.set_page_config(page_title="Luna Pro 主页", page_icon="💎", layout="wide")

# 调用工具箱的美化功能
utils.local_css()

# --- 1. 登录逻辑 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login_page():
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5'>💎 Luna Pro V18</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#666'>外贸英语 · 智能记忆 · 众筹词库</p>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab1, tab2 = st.tabs(["登录 (Login)", "注册 (Sign Up)"])
        db = utils.get_db()
        
        with tab1:
            u = st.text_input("用户名", key="l_u")
            p = st.text_input("密码", type="password", key="l_p")
            if st.button("🚀 登录", use_container_width=True):
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and utils.check_hashes(p, user['password']):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("账号或密码错误")
                else: st.error("❌ 无法连接数据库，请检查 IP 白名单")
        
        with tab2:
            nu = st.text_input("新用户名", key="r_u")
            np = st.text_input("设置密码", type="password", key="r_p")
            if st.button("✨ 注册新账号", use_container_width=True):
                if db is not None and nu and np:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}})
                        st.success("注册成功！请切换到登录页登录。")
                    else: st.warning("用户名已存在")

# --- 2. 主界面 (导航大厅) ---
if not st.session_state['logged_in']:
    login_page()
else:
    st.markdown(f"## 👋 Hi, {st.session_state['username']}")
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    
    # 导航卡片 1
    with c1:
        st.markdown("""
        <div class="nav-card">
            <span style="font-size:3rem">⚡</span>
            <h3>学习新词</h3>
            <p style="color:#666">按分类刷词 · 自动排除已学</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Learn (去学习)", use_container_width=True): 
            st.switch_page("pages/1_⚡_Learn.py")
        
    # 导航卡片 2
    with c2:
        st.markdown("""
        <div class="nav-card">
            <span style="font-size:3rem">🧠</span>
            <h3>智能复习</h3>
            <p style="color:#666">艾宾浩斯算法 · 巩固记忆</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Review (去复习)", use_container_width=True): 
            st.switch_page("pages/2_🧠_Review.py")
        
    # 导航卡片 3
    with c3:
        st.markdown("""
        <div class="nav-card">
            <span style="font-size:3rem">🚀</span>
            <h3>扩充词库</h3>
            <p style="color:#666">AI 自动生成 · 场景批量入库</p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Go Add (去扩词)", use_container_width=True): 
            st.switch_page("pages/3_🚀_Add.py")
            
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 退出登录"):
        st.session_state.clear()
        st.rerun()

import streamlit as st
import utils
import os
import datetime

# --- 强制写入配置文件 (解决颜色问题) ---
config_content = """
[theme]
base="light"
primaryColor="#4F46E5"
backgroundColor="#F3F4F6"
secondaryBackgroundColor="#FFFFFF"
textColor="#000000"
font="sans serif"
"""
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write(config_content)

st.set_page_config(page_title="Luna Pro 主页", page_icon="💎", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 自动登录
if not st.session_state['logged_in']:
    try:
        token = st.query_params.get("token")
        if token:
            db = utils.get_db()
            if db:
                user = db.users.find_one({"session_token": token})
                if user:
                    st.session_state.update({'logged_in':True, 'username':user['_id']})
                    st.rerun()
    except: pass

def login_page():
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5 !important'>💎 Luna Pro V28</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab1, tab2 = st.tabs(["登录", "注册"])
        db = utils.get_db()
        
        with tab1:
            u = st.text_input("用户名")
            p = st.text_input("密码", type="password")
            if st.button("🚀 登录", use_container_width=True, type="primary"):
                if db:
                    user = db.users.find_one({"_id": u})
                    if user and utils.check_hashes(p, user['password']):
                        # 生成 Token
                        import secrets
                        token = secrets.token_hex(16)
                        db.users.update_one({"_id": u}, {"$set": {"session_token": token}})
                        st.query_params["token"] = token
                        
                        st.session_state.update({'logged_in':True, 'username':u})
                        st.rerun()
                    else: st.error("账号或密码错误")
                else: st.error("数据库连接失败")
        
        with tab2:
            nu = st.text_input("新用户名")
            np = st.text_input("新密码", type="password")
            if st.button("✨ 注册", use_container_width=True):
                if db and nu:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}, "stats": {}})
                        st.success("注册成功！")
                    else: st.warning("用户已存在")

if not st.session_state['logged_in']:
    login_page()
else:
    # 侧边栏统计
    with st.sidebar:
        st.markdown("### 📊 学习数据")
        user = st.session_state['username']
        db = utils.get_db()
        if db:
            u_doc = db.users.find_one({"_id": user})
            stats = u_doc.get("stats", {}) if u_doc else {}
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            count = stats.get(today, 0)
            st.metric("今日打卡", count)
        
        st.divider()
        if st.button("退出登录"):
            if db: db.users.update_one({"_id": user}, {"$set": {"session_token": ""}})
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    # 主导航
    st.markdown(f"## 👋 Hi, {st.session_state['username']}")
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("<div class='nav-card'><h3>⚡ 学习新词</h3><p>按分类刷词</p></div>", unsafe_allow_html=True)
        if st.button("Go Learn", use_container_width=True): st.switch_page("pages/1_⚡_Learn.py")
    
    with c2:
        st.markdown("<div class='nav-card'><h3>🧠 智能复习</h3><p>巩固记忆</p></div>", unsafe_allow_html=True)
        if st.button("Go Review", use_container_width=True): st.switch_page("pages/2_🧠_Review.py")
        
    with c3:
        st.markdown("<div class='nav-card'><h3>🚀 扩充词库</h3><p>AI 自动生成</p></div>", unsafe_allow_html=True)
        if st.button("Go Add", use_container_width=True): st.switch_page("pages/3_🚀_Add.py")

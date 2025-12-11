import streamlit as st
import utils
import secrets # 用于生成安全密钥

st.set_page_config(page_title="Luna Pro 主页", page_icon="💎", layout="wide")

# 加载样式
utils.local_css()

# ==========================================
# 🔐 核心功能：自动登录检查 (Auto-Login)
# ==========================================
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# 1. 如果没登录，先看看地址栏有没有“通关令牌”
if not st.session_state['logged_in']:
    try:
        # 获取URL参数
        query_params = st.query_params
        token = query_params.get("token")
        
        if token:
            db = utils.get_db()
            if db is not None:
                # 去数据库查查这个令牌是谁的
                user = db.users.find_one({"session_token": token})
                if user:
                    # 找到了！自动登录
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = user['_id']
                    st.toast(f"🎉 欢迎回来, {user['_id']} (自动登录成功)")
    except:
        pass # 出错就不自动登录，走正常流程

# ==========================================
# 🚪 登录页面 (Login Page)
# ==========================================
def login_page():
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5 !important'>💎 Luna Pro V26</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align:center;color:#666'>自动保存进度 · 永久记住账号</p>", unsafe_allow_html=True)
    
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
                        # ✅ 登录成功：生成令牌，保存到数据库
                        token = secrets.token_hex(16)
                        db.users.update_one({"_id": u}, {"$set": {"session_token": token}})
                        
                        # 把令牌放到 URL 里，这样下次刷新就不会退出了
                        st.query_params["token"] = token
                        
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("密码错误")
                else: st.error("数据库连接失败")
        
        with tab2:
            nu = st.text_input("新用户名", key="r1")
            np = st.text_input("设置密码", type="password", key="r2")
            if st.button("✨ 注册", use_container_width=True):
                if db and nu:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}, "session_token": ""})
                        st.success("注册成功！请登录。")
                    else: st.warning("用户已存在")

# ==========================================
# 🏠 主大厅 (Main Hall)
# ==========================================
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
    
    # 退出登录：必须清除令牌，否则会自动登录回来
    if st.button("🚪 退出登录"):
        db = utils.get_db()
        if db:
            db.users.update_one({"_id": st.session_state['username']}, {"$set": {"session_token": ""}})
        st.query_params.clear() # 清空URL参数
        st.session_state.clear()
        st.rerun()

import streamlit as st
import utils
import secrets
import os
import datetime

# --- Force Light Theme ---
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

st.set_page_config(page_title="Luna Pro", page_icon="💎", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

# Auto Login
if not st.session_state['logged_in']:
    try:
        token = st.query_params.get("token")
        if token:
            db = utils.get_db()
            if db is not None:
                user = db.users.find_one({"session_token": token})
                if user:
                    st.session_state.update({'logged_in':True, 'username':user['_id']})
                    st.rerun()
    except: pass

def login_page():
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5 !important'>Luna Pro V33</h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        db = utils.get_db()
        
        with tab1:
            u = st.text_input("Username", key="login_u")
            p = st.text_input("Password", type="password", key="login_p")
            if st.button("Login", use_container_width=True, type="primary"):
                # FIX: Check if db is not None
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and utils.check_hashes(p, user['password']):
                        token = secrets.token_hex(16)
                        db.users.update_one({"_id": u}, {"$set": {"session_token": token}})
                        st.query_params["token"] = token
                        st.session_state.update({'logged_in':True, 'username':u})
                        st.rerun()
                    else: st.error("Wrong username or password")
                else: st.error("Database connection failed")
        
        with tab2:
            nu = st.text_input("New Username", key="reg_u")
            np = st.text_input("New Password", type="password", key="reg_p")
            if st.button("Register", use_container_width=True):
                if db is not None and nu:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}, "stats": {}})
                        st.success("Success! Please login.")
                    else: st.warning("User already exists")

if not st.session_state['logged_in']:
    login_page()
else:
    # --- Sidebar Stats (New Feature) ---
    with st.sidebar:
        st.markdown("### 📊 My Stats")
        user = st.session_state['username']
        db = utils.get_db()
        
        if db is not None:
            u_doc = db.users.find_one({"_id": user})
            
            # 1. Calculate Today's Words
            stats = u_doc.get("stats", {}) if u_doc else {}
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            count_today = stats.get(today, 0)
            
            # 2. Calculate Total Learned Words
            progress = u_doc.get("progress", {}) if u_doc else {}
            count_total = len(progress)
            
            # Display Metrics
            c_s1, c_s2 = st.columns(2)
            with c_s1:
                st.metric("🔥 Today", count_today)
            with c_s2:
                st.metric("🏆 Total", count_total)
        
        st.divider()
        if st.button("Logout"):
            if db is not None:
                db.users.update_one({"_id": user}, {"$set": {"session_token": ""}})
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    # --- Main Menu ---
    st.markdown(f"## Hi, {st.session_state['username']}")
    st.divider()
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("<div class='nav-card'><h3>Learn</h3><p>New Words</p></div>", unsafe_allow_html=True)
        if st.button("Go Learn", use_container_width=True): st.switch_page("pages/1_⚡_Learn.py")
    
    with c2:
        st.markdown("<div class='nav-card'><h3>Review</h3><p>Memory Check</p></div>", unsafe_allow_html=True)
        if st.button("Go Review", use_container_width=True): st.switch_page("pages/2_🧠_Review.py")
        
    with c3:
        st.markdown("<div class='nav-card'><h3>Add</h3><p>AI Generator</p></div>", unsafe_allow_html=True)
        if st.button("Go Add", use_container_width=True): st.switch_page("pages/3_🚀_Add.py")

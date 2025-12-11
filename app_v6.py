import streamlit as st
import utils

st.set_page_config(page_title="Luna Pro", page_icon="💎", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False

def login_page():
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5'>💎 Luna Pro V19</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        db = utils.get_db()
        
        with tab1:
            u = st.text_input("Username", key="l1")
            p = st.text_input("Password", type="password", key="l2")
            if st.button("🚀 Login", use_container_width=True):
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and utils.check_hashes(p, user['password']):
                        st.session_state['logged_in'] = True
                        st.session_state['username'] = u
                        st.rerun()
                    else: st.error("Error: Wrong password or username")
                else: st.error("Error: Database not connected")
        
        with tab2:
            nu = st.text_input("New Username", key="r1")
            np = st.text_input("New Password", type="password", key="r2")
            if st.button("✨ Register", use_container_width=True):
                if db is not None and nu:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": utils.make_hashes(np), "progress": {}})
                        st.success("Success! Please login.")
                    else: st.warning("User exists")

if not st.session_state['logged_in']:
    login_page()
else:
    st.markdown(f"## 👋 Hi, {st.session_state['username']}")
    st.divider()
    
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.markdown("<div class='nav-card'><h3>⚡ Learn</h3><p>New Words</p></div>", unsafe_allow_html=True)
        if st.button("Go Learn", use_container_width=True): st.switch_page("pages/1_⚡_Learn.py")
        
    with c2:
        st.markdown("<div class='nav-card'><h3>🧠 Review</h3><p>Memory Check</p></div>", unsafe_allow_html=True)
        if st.button("Go Review", use_container_width=True): st.switch_page("pages/2_🧠_Review.py")
        
    with c3:
        st.markdown("<div class='nav-card'><h3>🚀 Add</h3><p>AI Generator</p></div>", unsafe_allow_html=True)
        if st.button("Go Add", use_container_width=True): st.switch_page("pages/3_🚀_Add.py")
            
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("Logout"):
        st.session_state.clear()
        st.rerun()

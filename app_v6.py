import streamlit as st
import pandas as pd
import os
import time
import hashlib
import datetime
from gtts import gTTS
from io import BytesIO
import pymongo 

# --- 0. 基础配置 ---
st.set_page_config(page_title="Luna Pro V11 (纯净版)", page_icon="📝", layout="wide")

# 强制极简白底风格
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#2c3e50"\nbackgroundColor="#ffffff"\nsecondaryBackgroundColor="#f8f9fa"\ntextColor="#2d3436"\nfont="sans serif"\n')

def local_css():
    st.markdown("""
    <style>
    :root { --primary-color: #2c3e50; --text-color: #2d3436; }
    [data-testid="stAppViewContainer"] { background-color: #ffffff !important; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    [data-testid="stSidebar"] { background-color: #f8f9fa !important; border-right: 1px solid #eee; }
    
    /* 字体优化 */
    h1, h2, h3, p, div { font-family: 'Helvetica Neue', Arial, sans-serif; color: #2d3436 !important; }
    
    /* 单词主卡片 (极简风) */
    .word-header {
        text-align: center;
        margin-bottom: 30px;
        padding-bottom: 20px;
        border-bottom: 1px solid #eee;
    }
    .word-text { font-size: 4em; font-weight: 800; color: #2c3e50 !important; margin: 0; letter-spacing: -1px; }
    .phonetic-text { color: #7f8c8d !important; font-size: 1.4em; font-family: 'Georgia', serif; font-style: italic; margin-top: 5px; }
    .meaning-text { font-size: 1.8em; color: #2980b9 !important; font-weight: 600; margin-top: 10px; }
    
    /* 例句阶梯容器 */
    .sentence-container {
        margin-top: 20px;
        display: flex;
        flex-direction: column;
        gap: 15px;
    }
    
    /* 例句卡片 (分级颜色) */
    .sent-box {
        padding: 15px 20px;
        border-radius: 8px;
        background: #fff;
        border: 1px solid #eee;
        transition: transform 0.2s;
    }
    .sent-box:hover { transform: translateX(5px); border-color: #ccc; }
    
    .lvl-1 { border-left: 5px solid #2ecc71; } /* 简单 - 绿 */
    .lvl-2 { border-left: 5px solid #3498db; } /* 中等 - 蓝 */
    .lvl-3 { border-left: 5px solid #f1c40f; } /* 进阶 - 黄 */
    .lvl-4 { border-left: 5px solid #e67e22; } /* 困难 - 橙 */
    .lvl-5 { border-left: 5px solid #e74c3c; } /* 高难 - 红 */
    
    .sent-en { font-size: 1.2em; font-weight: 500; color: #2c3e50 !important; display: block; margin-bottom: 4px; }
    .sent-cn { font-size: 0.95em; color: #7f8c8d !important; }
    .sent-tag { font-size: 0.7em; text-transform: uppercase; letter-spacing: 1px; color: #95a5a6 !important; margin-bottom: 5px; display: block;}

    /* 按钮样式 */
    .stButton button { border-radius: 20px !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 1. 数据库连接 ---
@st.cache_resource
def init_connection():
    try: return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

client = init_connection()

def get_user_collection():
    if client: return client.luna_vocab_db.users
    return None

# --- 2. 数据库操作 ---
def get_user_from_db(username):
    coll = get_user_collection()
    if coll: return coll.find_one({"_id": username})
    return None

def create_user_in_db(username, password_hash):
    coll = get_user_collection()
    if coll:
        new_user = {
            "_id": username, "password": password_hash, "progress": {},
            "stats": {"streak": 0, "last_active_date": "", "daily_goal": 20, "today_count": 0, "last_count_date": ""}
        }
        try: coll.insert_one(new_user); return True
        except: return False
    return False

def update_user_progress(username, word, level, next_review):
    coll = get_user_collection()
    if coll:
        key = f"progress.{word}"
        coll.update_one({"_id": username}, {"$set": {key: {"level": level, "next_review": next_review}}})

def update_user_stats(username, stats_data):
    coll = get_user_collection()
    if coll: coll.update_one({"_id": username}, {"$set": {"stats": stats_data}})

# --- 3. 辅助函数 ---
@st.cache_data
def load_all_sheets():
    try:
        all_sheets = pd.read_excel("words.xlsx", sheet_name=None)
        valid_sheets = {}
        for name, df in all_sheets.items():
            if '单词 (Word)' in df.columns: valid_sheets[name] = df.dropna(subset=['单词 (Word)'])
        return valid_sheets
    except: return None

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h
def get_next_review_time(lvl):
    intervals = [0, 300, 86400, 259200, 604800, 1296000]
    sec = intervals[lvl] if lvl < len(intervals) else 2592000
    return time.time() + sec

def play_audio(text):
    try:
        sound_file = BytesIO()
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(sound_file)
        st.audio(sound_file, format='audio/mp3', start_time=0)
    except: st.toast("⚠️ Audio Error")

def get_today_str(): return datetime.date.today().strftime("%Y-%m-%d")

# --- 4. 登录逻辑 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

if st.session_state['logged_in']:
    current_user_data = get_user_from_db(st.session_state['username'])
    if not current_user_data:
        st.session_state['logged_in'] = False
        st.rerun()
else:
    current_user_data = None

def login_system():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>📝 Vocabulary Master</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            u = st.text_input("Username", key="l_u")
            p = st.text_input("Password", type="password", key="l_p")
            if st.button("Login", use_container_width=True):
                user = get_user_from_db(u)
                if user and check_hashes(p, user['password']):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.rerun()
                else: st.error("Error")
        with tab2:
            nu = st.text_input("New Username", key="r_u")
            np = st.text_input("New Password", type="password", key="r_p")
            if st.button("Sign Up", use_container_width=True):
                if nu and np: 
                    if create_user_in_db(nu, make_hashes(np)): st.success("Created!")
                    else: st.error("Exists")

# --- 5. 主程序 ---
if not st.session_state['logged_in']:
    login_system()
else:
    user_stats = current_user_data.get('stats', {"streak": 0, "daily_goal": 20, "today_count": 0})
    progress = current_user_data.get('progress', {})
    username = st.session_state['username']
    sheets_data = load_all_sheets()

    with st.sidebar:
        st.markdown(f"## 👤 {username}")
        
        today_str = get_today_str()
        db_updated = False
        if user_stats.get('last_count_date') != today_str:
            user_stats['today_count'] = 0
            user_stats['last_count_date'] = today_str
            db_updated = True
        
        goal = user_stats.get('daily_goal', 20)
        done = user_stats.get('today_count', 0)
        
        # 简单直接的显示
        st.caption("今日目标")
        st.progress(min(done / goal, 1.0))
        st.caption(f"{done} / {goal}")

        if db_updated: update_user_stats(username, user_stats)

        st.markdown("---")
        if st.button("Exit", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
        
        if not sheets_data: st.stop()
        cat_list = list(sheets_data.keys())
        sel_cat = st.selectbox("Current Book", cat_list)
        df_cur = sheets_data[sel_cat]
        mode = st.radio("Mode", ["Learn", "Review"])

    if mode == "Learn":
        all_ws = df_cur['单词 (Word)'].tolist()
        new_ws = [w for w in all_ws if w not in progress]
        if not new_ws:
            st.success("✅ All words learned in this list!")
        else:
            w_str = new_ws[0]
            row = df_cur[df_cur['单词 (Word)'] == w_str].iloc[0]
            
            # 极简单词头
            st.markdown(f"""
            <div class="word-header">
                <p class="word-text">{row['单词 (Word)']}</p>
                <div style="display:flex; justify-content:center; gap:15px; align-items:center;">
                    <p class="phonetic-text">{row['音标 (Phonetic)']}</p>
                </div>
                <p class="meaning-text">{row['中文 (Meaning)']}</p>
            </div>""", unsafe_allow_html=True)
            
            c_audio, c_rest = st.columns([1, 10])
            with c_audio:
                if st.button("🔊", help="Play Pronunciation"): play_audio(w_str)

            # 阶梯式例句展示 (支持5级)
            st.markdown("### 📚 Graded Sentences (由简入难)")
            
            levels = [
                ("Level 1 · Simple", "lvl-1"), 
                ("Level 2 · Daily", "lvl-2"), 
                ("Level 3 · Business", "lvl-3"), 
                ("Level 4 · Professional", "lvl-4"), 
                ("Level 5 · Advanced", "lvl-5")
            ]
            
            for i in range(1, 6):
                s_key = f"例句{i} (Sentence{i})"
                cn_key = f"例句{i}中文 (CN{i})"
                
                # 只有当Excel里填了这句时才显示
                if s_key in row and not pd.isna(row[s_key]):
                    level_name, css_class = levels[i-1]
                    with st.container():
                        st.markdown(f"""
                        <div class="sent-box {css_class}">
                            <span class="sent-tag">{level_name}</span>
                            <span class="sent-en">{row[s_key]}</span>
                            <span class="sent-cn">{row[cn_key]}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("🎧", key=f"s_btn_{i}"): play_audio(str(row[s_key]))
            
            st.markdown("<br><br>", unsafe_allow_html=True)
            
            # 极简按钮
            c1, c2, c3 = st.columns([1, 2, 1])
            with c2:
                if st.button("✅ 学会了", type="primary", use_container_width=True):
                    update_user_progress(username, w_str, 1, get_next_review_time(1))
                    if user_stats['last_count_date'] == today_str: user_stats['today_count'] += 1
                    else: 
                        user_stats['today_count'] = 1
                        user_stats['last_count_date'] = today_str
                    
                    # 连胜逻辑简化
                    last_active = user_stats.get('last_active_date', '')
                    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
                    if last_active != today_str:
                        if last_active == yesterday: user_stats['streak'] += 1
                        else: user_stats['streak'] = 1
                    user_stats['last_active_date'] = today_str
                    
                    update_user_stats(username, user_stats)
                    st.rerun()

    elif mode == "Review":
        due_list = [w for w in progress if progress[w]['next_review'] < time.time()]
        if not due_list: st.info("🎉 No reviews pending.")
        else:
            w_str = due_list[0]
            row = None
            for sheet in sheets_data.values():
                if w_str in sheet['单词 (Word)'].values:
                    row = sheet[sheet['单词 (Word)'] == w_str].iloc[0]
                    break
            
            if row is not None:
                st.markdown(f"<h1 style='text-align:center;'>{w_str}</h1>", unsafe_allow_html=True)
                with st.expander("Show Meaning"): st.info(row['中文 (Meaning)'])
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❌ Forgot", use_container_width=True):
                        update_user_progress(username, w_str, 1, get_next_review_time(1))
                        st.rerun()
                with c2:
                    if st.button("✅ Remember", use_container_width=True):
                        nl = progress[w_str]['level'] + 1
                        update_user_progress(username, w_str, nl, get_next_review_time(nl))
                        st.rerun()
            else:
                 update_user_progress(username, w_str, 0, 0)
                 st.rerun()

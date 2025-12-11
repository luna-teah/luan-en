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
st.set_page_config(page_title="Luna Pro V10 (云数据库版)", page_icon="☁️", layout="wide")

# 强制浅色模式
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#6c5ce7"\nbackgroundColor="#ffffff"\nsecondaryBackgroundColor="#f0f2f6"\ntextColor="#2d3436"\nfont="sans serif"\n')

def local_css():
    st.markdown("""
    <style>
    :root { --primary-color: #6c5ce7; --background-color: #ffffff; --secondary-background-color: #f0f2f6; --text-color: #2d3436; }
    [data-testid="stAppViewContainer"] { background-color: #f4f6f9 !important; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; }
    h1, h2, h3, h4, h5, h6, p, li, span, div, label { color: #2d3436 !important; }
    .main-card { background: #ffffff !important; padding: 40px; border-radius: 20px; box-shadow: 0 10px 30px rgba(0,0,0,0.08); text-align: center; margin-bottom: 25px; border-top: 6px solid #6c5ce7; }
    .word-text { font-family: 'Arial', sans-serif; font-size: 3.5em; font-weight: 800; color: #2d3436 !important; margin: 0; }
    .phonetic-text { color: #636e72 !important; font-size: 1.2em; margin-bottom: 15px; }
    .meaning-text { font-size: 1.5em; color: #0984e3 !important; font-weight: 600; }
    .tag-container { display: flex; justify-content: center; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
    .tag-syn { background-color: #e3f9e5 !important; color: #00b894 !important; padding: 5px 15px; border-radius: 20px; border: 1px solid #b2bec3; }
    .tag-ant { background-color: #ffeaa7 !important; color: #d63031 !important; padding: 5px 15px; border-radius: 20px; border: 1px solid #b2bec3; }
    .sent-box { background: #ffffff !important; border-left: 4px solid #74b9ff; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .memory-image-container img { width: 100%; border-radius: 15px; box-shadow: 0 5px 15px rgba(0,0,0,0.1); object-fit: cover; max-height: 400px; }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 1. 数据库连接 ---
@st.cache_resource
def init_connection():
    try:
        return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except Exception as e:
        return None

client = init_connection()

def get_user_collection():
    if client: return client.luna_vocab_db.users
    return None

# --- 2. 数据库操作 ---
def get_user_from_db(username):
    coll = get_user_collection()
    if coll is not None: return coll.find_one({"_id": username})
    return None

def create_user_in_db(username, password_hash):
    coll = get_user_collection()
    if coll is not None:
        new_user = {
            "_id": username,
            "password": password_hash,
            "progress": {},
            "stats": {"streak": 0, "last_active_date": "", "daily_goal": 10, "today_count": 0, "last_count_date": ""}
        }
        try:
            coll.insert_one(new_user)
            return True
        except: return False
    return False

def update_user_progress(username, word, level, next_review):
    coll = get_user_collection()
    if coll is not None:
        key = f"progress.{word}"
        coll.update_one({"_id": username}, {"$set": {key: {"level": level, "next_review": next_review}}})

def update_user_stats(username, stats_data):
    coll = get_user_collection()
    if coll is not None:
        coll.update_one({"_id": username}, {"$set": {"stats": stats_data}})

# --- 3. 辅助函数 ---
@st.cache_data
def load_all_sheets():
    try:
        all_sheets = pd.read_excel("words.xlsx", sheet_name=None)
        valid_sheets = {}
        for name, df in all_sheets.items():
            if '单词 (Word)' in df.columns:
                valid_sheets[name] = df.dropna(subset=['单词 (Word)'])
        return valid_sheets
    except: return None

def make_hashes(password): return hashlib.sha256(str.encode(password)).hexdigest()
def check_hashes(password, hashed_text): return make_hashes(password) == hashed_text
def get_next_review_time(level):
    intervals = [0, 300, 86400, 259200, 604800, 1296000]
    seconds = intervals[level] if level < len(intervals) else 2592000
    return time.time() + seconds

def play_audio(text):
    try:
        sound_file = BytesIO()
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(sound_file)
        st.audio(sound_file, format='audio/mp3', start_time=0)
    except: st.toast("⚠️ 语音生成失败")

def show_memory_anchor(prompt_text, word_info=""):
    prompt_str = str(prompt_text).strip()
    if prompt_str.startswith("http"):
        st.markdown(f'<div class="memory-image-container"><img src="{prompt_str}"></div><p style="text-align:center;color:#666;font-size:0.9em;">🎯 记忆锚点</p>', unsafe_allow_html=True)
        return
    if prompt_str and prompt_str != 'nan':
        ai_url = f"https://image.pollinations.ai/prompt/{prompt_str}, professional illustration"
        st.image(ai_url, caption="🤖 AI 绘图", use_container_width=True)
    else:
        st.info("💡 Tip: Excel填入图片链接，即可显示精准记忆图！")

def get_today_str(): return datetime.date.today().strftime("%Y-%m-%d")

# --- 4. 登录逻辑 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

if st.session_state['logged_in']:
    current_user_data = get_user_from_db(st.session_state['username'])
    if not current_user_data:
        st.error("数据库连接中断，请重新登录")
        st.session_state['logged_in'] = False
        st.rerun()
else:
    current_user_data = None

def login_system():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #2d3436 !important;'>☁️ Luna Pro V10</h1>", unsafe_allow_html=True)
        st.caption("Data Powered by MongoDB Atlas")
        
        tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
        with tab1:
            u = st.text_input("用户名", key="l_u")
            p = st.text_input("密码", type="password", key="l_p")
            if st.button("🚀 登录", use_container_width=True):
                user = get_user_from_db(u)
                if user and check_hashes(p, user['password']):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.success("登录成功！")
                    time.sleep(1)
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        with tab2:
            nu = st.text_input("新用户名", key="r_u")
            np = st.text_input("设置密码", type="password", key="r_p")
            if st.button("✨ 注册 (数据永久保存)", use_container_width=True):
                if not nu or not np: st.warning("不能为空")
                elif get_user_from_db(nu): st.warning("用户名已存在")
                else:
                    if create_user_in_db(nu, make_hashes(np)): st.success("注册成功！请登录。")
                    else: st.error("注册失败，请检查网络。")

# --- 5. 主程序 ---
if not st.session_state['logged_in']:
    login_system()
else:
    user_stats = current_user_data.get('stats', {"streak": 0, "last_active_date": "", "daily_goal": 10, "today_count": 0, "last_count_date": ""})
    progress = current_user_data.get('progress', {})
    username = st.session_state['username']
    sheets_data = load_all_sheets()

    with st.sidebar:
        st.title(f"Hi, {username}")
        st.caption("🟢 云端已连接")
        
        today_str = get_today_str()
        db_updated = False
        if user_stats.get('last_count_date') != today_str:
            user_stats['today_count'] = 0
            user_stats['last_count_date'] = today_str
            db_updated = True
        
        goal = user_stats.get('daily_goal', 10)
        done = user_stats.get('today_count', 0)
        
        if db_updated: update_user_stats(username, user_stats)

        st.markdown("### 🔥 每日挑战")
        st.metric("今日单词", f"{done} / {goal}")
        st.progress(min(done / goal, 1.0))

        if st.button("🚪 退出", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
        
        if not sheets_data: st.stop()
        cat_list = list(sheets_data.keys())
        sel_cat = st.selectbox("📚 单词书架", cat_list)
        df_cur = sheets_data[sel_cat]
        mode = st.radio("模式", ["📖 沉浸背词", "🔄 智能复习", "📊 数据中心"])

    if mode == "📊 数据中心":
        st.markdown("<h1 style='color:#2d3436 !important'>📊 学习数据</h1>", unsafe_allow_html=True)
        st.info("✅ 您的数据已安全存储在 MongoDB 云端，永不丢失！")
        st.bar_chart({"今日": done, "目标": goal})

    elif mode == "📖 沉浸背词":
        all_ws = df_cur['单词 (Word)'].tolist()
        new_ws = [w for w in all_ws if w not in progress]
        if not new_ws:
            st.balloons()
            st.success("🎉 本册学完！")
        else:
            w_str = new_ws[0]
            row = df_cur[df_cur['单词 (Word)'] == w_str].iloc[0]
            
            syns = str(row.get('近义词 (Synonyms)', '')).replace('nan', '')
            ants = str(row.get('反义词 (Antonyms)', '')).replace('nan', '')
            tags_html = ""
            if syns: tags_html += f"<span class='tag-syn'>🔗 近: {syns}</span>"
            if ants: tags_html += f"<span class='tag-ant'>⚡ 反: {ants}</span>"

            st.markdown(f"""
            <div class="main-card">
                <p class="word-text">{row['单词 (Word)']}</p>
                <p class="phonetic-text">{row['音标 (Phonetic)']}</p>
                <p class="meaning-text">{row['中文 (Meaning)']}</p>
                <div class="tag-container">{tags_html}</div>
            </div>""", unsafe_allow_html=True)
            
            c_a, c_b = st.columns([1,5])
            with c_a: 
                if st.button("🔊 播放", use_container_width=True): play_audio(w_str)
            
            c1, c2 = st.columns(2)
            with c1: 
                st.info(f"🧠 {row['脑洞联想 (Mnemonic)']}")
                st.caption(f"🌲 {row['词源/逻辑 (Etymology)']}")
            with c2:
                raw_prompt = str(row.get('语境图描述 (ImagePrompt)', '')).replace('nan', '').strip()
                show_memory_anchor(raw_prompt, w_str)

            st.markdown("<br>", unsafe_allow_html=True)
            
            if st.button("✅ 我学会了 (同步云端)", type="primary", use_container_width=True):
                update_user_progress(username, w_str, 1, get_next_review_time(1))
                if user_stats['last_count_date'] == today_str: user_stats['today_count'] += 1
                else: 
                    user_stats['today_count'] = 1
                    user_stats['last_count_date'] = today_str
                update_user_stats(username, user_stats)
                st.toast("✅ 已保存到云端")
                time.sleep(0.5)
                st.rerun()

    elif mode == "🔄 智能复习":
        due_list = [w for w in progress if progress[w]['next_review'] < time.time()]
        if not due_list: st.success("🎉 复习清空！")
        else:
            w_str = due_list[0]
            row = None
            for sheet in sheets_data.values():
                if w_str in sheet['单词 (Word)'].values:
                    row = sheet[sheet['单词 (Word)'] == w_str].iloc[0]
                    break
            
            if row is not None:
                st.markdown(f"## 复习: {w_str}")
                with st.expander("提示"): st.info(row['中文 (Meaning)'])
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❌ 忘了", use_container_width=True):
                        update_user_progress(username, w_str, 1, get_next_review_time(1))
                        st.rerun()
                with c2:
                    if st.button("✅ 记得", use_container_width=True):
                        nl = progress[w_str]['level'] + 1
                        update_user_progress(username, w_str, nl, get_next_review_time(nl))
                        st.rerun()
            else:
                 update_user_progress(username, w_str, 0, 0) # 容错
                 st.rerun()

import streamlit as st
import pandas as pd
import json
import os
import time
import hashlib
import datetime
from gtts import gTTS
from io import BytesIO

# --- 0. 🛑 强制配置文件 ---
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('''
[theme]
base="light"
primaryColor="#6c5ce7"
backgroundColor="#ffffff"
secondaryBackgroundColor="#f0f2f6"
textColor="#2d3436"
font="sans serif"
''')

# --- 1. 全局配置 ---
st.set_page_config(page_title="Luna Pro 单词通 V9.3", page_icon="🎯", layout="wide")

# --- 2. 🎨 UI 美学工程 ---
def local_css():
    st.markdown("""
    <style>
    :root { --primary-color: #6c5ce7; --background-color: #ffffff; --secondary-background-color: #f0f2f6; --text-color: #2d3436; }
    [data-testid="stAppViewContainer"] { background-color: #f4f6f9 !important; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    [data-testid="stSidebar"] { background-color: #ffffff !important; }
    h1, h2, h3, h4, h5, h6, p, li, span, div, label { color: #2d3436 !important; }
    
    .main-card {
        background: #ffffff !important;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 25px;
        border-top: 6px solid #6c5ce7;
    }
    .word-text { font-family: 'Arial', sans-serif; font-size: 3.5em; font-weight: 800; color: #2d3436 !important; margin: 0; }
    .phonetic-text { color: #636e72 !important; font-size: 1.2em; margin-bottom: 15px; }
    .meaning-text { font-size: 1.5em; color: #0984e3 !important; font-weight: 600; }
    
    .tag-container { display: flex; justify-content: center; gap: 10px; margin-top: 15px; flex-wrap: wrap; }
    .tag-syn { background-color: #e3f9e5 !important; color: #00b894 !important; padding: 5px 15px; border-radius: 20px; border: 1px solid #b2bec3; }
    .tag-ant { background-color: #ffeaa7 !important; color: #d63031 !important; padding: 5px 15px; border-radius: 20px; border: 1px solid #b2bec3; }
    
    .sent-box { background: #ffffff !important; border-left: 4px solid #74b9ff; padding: 15px; margin-bottom: 10px; border-radius: 8px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    
    /* V9.3 新增：图片容器样式，支持 GIF */
    .memory-image-container img {
        width: 100%;
        border-radius: 15px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
        object-fit: cover;
        max-height: 400px; /* 限制最大高度，防止图太长 */
    }
    </style>
    """, unsafe_allow_html=True)

local_css()

# --- 3. 核心功能函数 ---

@st.cache_data
def load_all_sheets():
    try:
        all_sheets = pd.read_excel("words.xlsx", sheet_name=None)
        valid_sheets = {}
        for name, df in all_sheets.items():
            if '单词 (Word)' in df.columns:
                valid_sheets[name] = df.dropna(subset=['单词 (Word)'])
        return valid_sheets
    except Exception as e:
        return None

def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    return make_hashes(password) == hashed_text

USER_DB_FILE = "users_db.json"

def load_user_db():
    if not os.path.exists(USER_DB_FILE): return {}
    with open(USER_DB_FILE, "r") as f: return json.load(f)

def save_user_db(data):
    with open(USER_DB_FILE, "w") as f: json.dump(data, f)

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
    except:
        st.toast("⚠️ 语音生成失败")

# --- 🔥 V9.3 核心升级：精准记忆锚点展示函数 ---
def show_memory_anchor(prompt_text, word_info=""):
    prompt_str = str(prompt_text).strip()
    
    # 1. 优先检查是否是用户提供的精确链接 (支持 JPG, PNG, GIF)
    if prompt_str.startswith("http"):
        # 使用 Markdown 来更好地支持 GIF 动图显示
        st.markdown(f"""
        <div class="memory-image-container">
            <img src="{prompt_str}" alt="Memory Anchor">
        </div>
        <p style="text-align: center; color: #666; font-size: 0.9em;">🎯 精准记忆锚点 (Manual Select)</p>
        """, unsafe_allow_html=True)
        return

    # 2. 如果没有链接，再尝试用 AI 生成 (作为降级备份)
    # 只有当有描述文字时才生成，避免生成无意义的图
    if prompt_str and prompt_str != 'nan':
        ai_url = f"https://image.pollinations.ai/prompt/{prompt_str}, professional illustration"
        st.image(ai_url, caption=f"🤖 AI 辅助绘图 (仅供参考)", use_container_width=True)
    else:
        # 如果什么都没填，显示一个占位提示
        st.info("💡 Tip: 在 Excel 的 [语境图描述] 列粘贴一个图片或动图网址，这里就能显示你的专属记忆图像了！")

# --- 4. 日期处理 ---
def get_today_str():
    return datetime.date.today().strftime("%Y-%m-%d")

# --- 5. 登录系统 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

def login_system():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center; color: #2d3436 !important;'>🎯 Luna Pro V9.3</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["🔑 登录", "📝 注册"])
        users = load_user_db()
        with tab1:
            u = st.text_input("用户名", key="l_u")
            p = st.text_input("密码", type="password", key="l_p")
            if st.button("🚀 登录", use_container_width=True):
                if u in users and check_hashes(p, users[u]['password']):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        with tab2:
            nu = st.text_input("新用户名", key="r_u")
            np = st.text_input("设置密码", type="password", key="r_p")
            if st.button("✨ 注册", use_container_width=True):
                if nu in users:
                    st.warning("用户已存在")
                elif nu and np:
                    users[nu] = {
                        "password": make_hashes(np), 
                        "progress": {},
                        "stats": {"streak": 0, "last_active_date": "", "daily_goal": 10, "today_count": 0, "last_count_date": ""}
                    }
                    save_user_db(users)
                    st.success("注册成功！")

# --- 6. 主界面逻辑 ---

if not st.session_state['logged_in']:
    login_system()
else:
    users = load_user_db()
    current_user = st.session_state['username']
    if 'stats' not in users[current_user]:
        users[current_user]['stats'] = {"streak": 0, "last_active_date": "", "daily_goal": 10, "today_count": 0, "last_count_date": ""}
    
    user_stats = users[current_user]['stats']
    progress = users[current_user].get('progress', {})
    sheets_data = load_all_sheets()

    with st.sidebar:
        st.title(f"Hi, {current_user}")
        
        today_str = get_today_str()
        if user_stats.get('last_count_date') != today_str:
            user_stats['today_count'] = 0
            user_stats['last_count_date'] = today_str
            save_user_db(users) 
        
        goal = user_stats.get('daily_goal', 10)
        done = user_stats.get('today_count', 0)
        
        last_active = user_stats.get('last_active_date', '')
        yesterday = (datetime.date.today() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        streak = user_stats.get('streak', 0)
        display_streak = streak
        if last_active != today_str and last_active != yesterday and last_active != "":
            display_streak = 0 

        st.markdown("### 🔥 每日挑战")
        c_s1, c_s2 = st.columns(2)
        c_s1.metric("坚持天数", f"{display_streak} 天")
        c_s2.metric("今日单词", f"{done} / {goal}")
        st.progress(min(done / goal, 1.0))
        if done >= goal: st.success("🎉 目标达成！")

        with st.expander("⚙️ 设置每日目标"):
            new_goal = st.slider("每天背多少个？", 5, 50, goal)
            if new_goal != goal:
                users[current_user]['stats']['daily_goal'] = new_goal
                save_user_db(users)
                st.rerun()

        st.markdown("---")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
        
        if sheets_data is None:
            st.error("Excel读取失败")
            st.stop()

        cat_list = list(sheets_data.keys())
        sel_cat = st.selectbox("📚 单词书架", cat_list)
        df_cur = sheets_data[sel_cat]
        mode = st.radio("模式", ["📖 沉浸背词", "🔄 智能复习", "📊 数据中心"])

    if mode == "📊 数据中心":
        st.markdown("<h1 style='color:#2d3436 !important'>📊 学习数据</h1>", unsafe_allow_html=True)
        st.bar_chart({"今日": done, "目标": goal})

    elif mode == "📖 沉浸背词":
        all_ws = df_cur['单词 (Word)'].tolist()
        new_ws = [w for w in all_ws if w not in progress]
        
        if not new_ws:
            st.balloons()
            st.success("🎉 本册单词全部学完！")
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
            </div>
            """, unsafe_allow_html=True)
            
            c_audio, c_b = st.columns([1,5])
            with c_audio:
                if st.button("🔊 播放", use_container_width=True): play_audio(w_str)

            c_left, c_right = st.columns(2)
            with c_left:
                st.info(f"🧠 **脑洞**: {row['脑洞联想 (Mnemonic)']}")
                st.caption(f"🌲 **词源**: {row['词源/逻辑 (Etymology)']}")
            
            with c_right:
                # --- 🔥 V9.3 调用新的展示函数 ---
                raw_prompt = str(row.get('语境图描述 (ImagePrompt)', '')).replace('nan', '').strip()
                show_memory_anchor(raw_prompt, word_info=w_str)
                # -------------------------------

            st.markdown("<h3 style='color:#2d3436 !important'>🗣️ 真实语境</h3>", unsafe_allow_html=True)
            for i in range(1, 4):
                s_key, cn_key = f"例句{i} (Sentence{i})", f"例句{i}中文 (CN{i})"
                if s_key in row and not pd.isna(row[s_key]):
                    with st.container():
                        st.markdown(f"<div class='sent-box'><b>{row[s_key]}</b><br><span>{row[cn_key]}</span></div>", unsafe_allow_html=True)
                        if st.button("🎧", key=f"btn_s{i}"): play_audio(str(row[s_key]))

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ 我学会了 (打卡 +1)", type="primary", use_container_width=True):
                users[current_user]['progress'][w_str] = {"level": 1, "next_review": get_next_review_time(1)}
                if users[current_user]['stats']['last_count_date'] == today_str:
                    users[current_user]['stats']['today_count'] += 1
                else:
                    users[current_user]['stats']['today_count'] = 1
                    users[current_user]['stats']['last_count_date'] = today_str
                
                if last_active == today_str: pass
                elif last_active == yesterday: users[current_user]['stats']['streak'] += 1
                else: users[current_user]['stats']['streak'] = 1
                
                users[current_user]['stats']['last_active_date'] = today_str
                save_user_db(users)
                st.balloons()
                time.sleep(0.5)
                st.rerun()

    elif mode == "🔄 智能复习":
        user_prog = users[current_user].get('progress', {})
        due_list = [w for w in user_prog if user_prog[w]['next_review'] < time.time()]
        if not due_list:
            st.success("🎉 复习任务清空！")
        else:
            w_str = due_list[0]
            row = None
            for sheet in sheets_data.values():
                if w_str in sheet['单词 (Word)'].values:
                    row = sheet[sheet['单词 (Word)'] == w_str].iloc[0]
                    break
            
            if row is not None:
                st.markdown(f"# 复习: {w_str}")
                with st.expander("查看提示"):
                    st.info(row['中文 (Meaning)'])
                    # 复习模式也调用新函数
                    raw_prompt = str(row.get('语境图描述 (ImagePrompt)', '')).replace('nan', '').strip()
                    show_memory_anchor(raw_prompt, word_info=w_str)

                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❌ 忘了", use_container_width=True):
                        users[current_user]['progress'][w_str]['level'] = 1
                        save_user_db(users)
                        st.rerun()
                with c2:
                    if st.button("✅ 记得", use_container_width=True):
                        nl = users[current_user]['progress'][w_str]['level'] + 1
                        users[current_user]['progress'][w_str]['next_review'] = get_next_review_time(nl)
                        save_user_db(users)
                        st.rerun()
            else:
                 del users[current_user]['progress'][w_str]
                 save_user_db(users)
                 st.rerun()
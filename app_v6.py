import streamlit as st
import pandas as pd
import json
import os
import time
import hashlib
from gtts import gTTS
from io import BytesIO

# --- 1. 全局配置 ---
st.set_page_config(page_title="Luna Pro 单词通 V8", page_icon="💎", layout="wide")

# --- 2. 🎨 UI 美学工程 (CSS V8.0) ---
def local_css():
    st.markdown("""
    <style>
    /* 全局背景优化 */
    .stApp { background-color: #f4f6f9; }
    
    /* 单词主卡片 */
    .main-card {
        background: white;
        padding: 40px;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        text-align: center;
        margin-bottom: 25px;
        border-top: 6px solid #6c5ce7;
    }
    .word-text {
        font-family: 'Arial', sans-serif;
        font-size: 3.5em;
        font-weight: 800;
        color: #2d3436;
        margin: 0;
    }
    .phonetic-text {
        font-family: 'Courier New', monospace;
        color: #636e72;
        font-size: 1.2em;
        margin-bottom: 15px;
    }
    .meaning-text {
        font-size: 1.5em;
        color: #0984e3;
        font-weight: 600;
    }
    
    /* 近义词/反义词 胶囊标签 */
    .tag-container {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-top: 15px;
        flex-wrap: wrap;
    }
    .tag-syn {
        background-color: #e3f9e5; /* 浅绿 */
        color: #00b894;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: 600;
        border: 1px solid #b2bec3;
    }
    .tag-ant {
        background-color: #ffeaa7; /* 浅黄 */
        color: #d63031;
        padding: 5px 15px;
        border-radius: 20px;
        font-size: 0.9em;
        font-weight: 600;
        border: 1px solid #b2bec3;
    }
    
    /* 例句盒子 */
    .sent-box {
        background: #ffffff;
        border-left: 4px solid #74b9ff;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 8px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
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
        st.toast("⚠️ 网络波动，语音生成失败")

def show_ai_image(prompt_text):
    if not prompt_text or pd.isna(prompt_text): return
    prompt_str = str(prompt_text).strip()
    if prompt_str.startswith("http"):
        st.image(prompt_str, use_container_width=True)
    else:
        ai_url = f"https://image.pollinations.ai/prompt/{prompt_str}"
        st.image(ai_url, caption=f"🎨 AI Vision", use_container_width=True)

# --- 4. 登录系统 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

def login_system():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h1 style='text-align: center;'>💎 Luna Pro</h1>", unsafe_allow_html=True)
        st.info("专业的单词记忆伴侣 | Professional Vocabulary Partner")
        
        tab1, tab2 = st.tabs(["🔑 登录账号", "📝 注册新用户"])
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
                    users[nu] = {"password": make_hashes(np), "progress": {}}
                    save_user_db(users)
                    st.success("注册成功！请登录。")

# --- 5. 主界面逻辑 ---

if not st.session_state['logged_in']:
    login_system()
else:
    users = load_user_db()
    current_user = st.session_state['username']
    progress = users[current_user].get('progress', {})
    sheets_data = load_all_sheets()

    # === 侧边栏 ===
    with st.sidebar:
        st.title(f"Hi, {current_user}")
        if st.button("🚪 退出", use_container_width=True):
            st.session_state['logged_in'] = False
            st.rerun()
        
        if sheets_data is None:
            st.error("Excel读取失败")
            st.stop()

        st.markdown("---")
        cat_list = list(sheets_data.keys())
        sel_cat = st.selectbox("📚 选择单词书", cat_list)
        
        df_cur = sheets_data[sel_cat]
        total = len(df_cur)
        learned = sum(1 for w in df_cur['单词 (Word)'] if w in progress and progress[w]['level'] > 0)
        
        st.metric("本册进度", f"{learned} / {total}")
        st.progress(learned / total if total > 0 else 0)
        
        st.markdown("---")
        mode = st.radio("模式选择", ["📖 沉浸背词", "🔄 智能复习", "📊 数据中心"])

    # === 功能区 ===
    if mode == "📊 数据中心":
        st.title("📊 学习仪表盘")
        c1, c2 = st.columns(2)
        c1.metric("累计掌握单词", f"{len(progress)}", "+5 Today")
        c2.metric("当前分类", sel_cat)
        st.bar_chart({"已学": learned, "未学": total-learned})

    elif mode == "📖 沉浸背词":
        all_ws = df_cur['单词 (Word)'].tolist()
        new_ws = [w for w in all_ws if w not in progress]
        
        if not new_ws:
            st.success("🎉 本册单词全部学完！")
        else:
            w_str = new_ws[0]
            row = df_cur[df_cur['单词 (Word)'] == w_str].iloc[0]
            
            # === 1. 单词主卡片 (HTML/CSS) ===
            syns = str(row.get('近义词 (Synonyms)', '')).replace('nan', '')
            ants = str(row.get('反义词 (Antonyms)', '')).replace('nan', '')
            
            # 生成标签 HTML
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
            
            # 播放按钮
            c_audio, c_b = st.columns([1,5])
            with c_audio:
                if st.button("🔊 播放", use_container_width=True): play_audio(w_str)

            # === 2. 左右分栏：记忆 & 视觉 ===
            c_left, c_right = st.columns(2)
            
            with c_left:
                st.info(f"🧠 **脑洞联想**: {row['脑洞联想 (Mnemonic)']}")
                st.caption(f"🌲 **词源**: {row['词源/逻辑 (Etymology)']}")
                
            with c_right:
                # 只有这里显示图片
                show_ai_image(row.get('语境图描述 (ImagePrompt)', ''))

            # === 3. 五维例句库 ===
            st.markdown("### 🗣️ 真实语境")
            for i in range(1, 6):
                s_key, cn_key = f"例句{i} (Sentence{i})", f"例句{i}中文 (CN{i})"
                if s_key in row and not pd.isna(row[s_key]):
                    with st.container():
                        st.markdown(f"""
                        <div class="sent-box">
                            <b>{row[s_key]}</b><br>
                            <span style='color:#888; font-size:0.9em;'>{row[cn_key]}</span>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("🎧", key=f"btn_s{i}"): play_audio(str(row[s_key]))

            # === 4. AI 造句私教 ===
            st.markdown("---")
            user_input = st.text_input(f"✍️ 试着用 {w_str} 造个句子 (AI 检测):")
            if user_input:
                if w_str.lower() in user_input.lower():
                    st.balloons()
                    st.success("✅ 完美！你已经掌握了这个词的用法！")
                else:
                    st.warning(f"⚠️ 句子中好像没包含 {w_str}，请检查拼写。")

            # === 5. 底部确认 ===
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ 我学会了，下一个", type="primary", use_container_width=True):
                users[current_user]['progress'][w_str] = {"level": 1, "next_review": get_next_review_time(1)}
                save_user_db(users)
                st.rerun()

    elif mode == "🔄 智能复习":
        user_prog = users[current_user].get('progress', {})
        due_list = [w for w in user_prog if user_prog[w]['next_review'] < time.time()]
        
        if not due_list:
            st.success("🎉 复习任务清空！")
        else:
            w_str = due_list[0]
            # 找数据
            row = None
            for sheet in sheets_data.values():
                if w_str in sheet['单词 (Word)'].values:
                    row = sheet[sheet['单词 (Word)'] == w_str].iloc[0]
                    break
            
            if row is None:
                del users[current_user]['progress'][w_str]
                save_user_db(users)
                st.rerun()
            else:
                st.markdown(f"# 复习: {w_str}")
                
                with st.expander("🔍 查看提示"):
                    st.info(row['中文 (Meaning)'])
                    st.write(f"🧠 {row['脑洞联想 (Mnemonic)']}")
                    syns = str(row.get('近义词 (Synonyms)', '')).replace('nan', '')
                    if syns: st.write(f"🔗 近义词: {syns}")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❌ 忘了", use_container_width=True):
                        users[current_user]['progress'][w_str]['level'] = 1
                        users[current_user]['progress'][w_str]['next_review'] = get_next_review_time(1)
                        save_user_db(users)
                        st.rerun()
                with c2:
                    if st.button("✅ 记得", use_container_width=True):
                        nl = users[current_user]['progress'][w_str]['level'] + 1
                        users[current_user]['progress'][w_str]['level'] = nl
                        users[current_user]['progress'][w_str]['next_review'] = get_next_review_time(nl)
                        save_user_db(users)
                        st.rerun()
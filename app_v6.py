import streamlit as st
import pandas as pd
import json
import os
import time
from gtts import gTTS
from io import BytesIO  # <--- 新增这个库，用于在内存里处理声音

# --- 1. 配置页面 ---
st.set_page_config(page_title="Luna单词通 V6.1 (云端优化版)", page_icon="🌐", layout="centered")

# --- 2. 核心功能函数 ---

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

def load_user_progress(username):
    filename = f"progress_{username}.json"
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_user_progress(username, data):
    filename = f"progress_{username}.json"
    with open(filename, "w") as f:
        json.dump(data, f)

def get_next_review_time(level):
    intervals = [0, 300, 86400, 259200, 604800, 1296000]
    seconds = intervals[level] if level < len(intervals) else 2592000
    return time.time() + seconds

# --- 🔥 重点修改：云端声音优化函数 ---
def play_audio(text):
    try:
        # 1. 创建一个内存里的"虚拟文件"
        sound_file = BytesIO()
        # 2. 让 AI 把声音直接写进内存，而不是存到硬盘
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(sound_file)
        # 3. 播放
        st.audio(sound_file, format='audio/mp3', start_time=0)
    except Exception as e:
        st.error(f"语音生成失败: {e}")

# --- 3. 登录界面逻辑 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

def login_page():
    st.title("🔐 欢迎来到 Luna 单词通")
    st.info("请登录以加载你的专属记忆进度")
    
    with st.form("login_form"):
        username = st.text_input("用户名 (User Name):", placeholder="例如: luna")
        submit = st.form_submit_button("登录 / 注册")
        
        if submit:
            if username.strip():
                st.session_state['logged_in'] = True
                st.session_state['username'] = username.strip()
                st.rerun()
            else:
                st.error("请输入用户名！")

# --- 4. 主程序逻辑 ---

if not st.session_state['logged_in']:
    login_page()
else:
    current_user = st.session_state['username']
    progress = load_user_progress(current_user)
    sheets_data = load_all_sheets()

    with st.sidebar:
        st.title(f"👤 学员: {current_user}")
        if st.button("退出登录"):
            st.session_state['logged_in'] = False
            st.rerun()
            
        st.divider()
        
        if sheets_data is None:
            st.error("❌ 找不到 words.xlsx")
            st.stop()

        # 自动识别 Excel 里的标签页
        category_list = list(sheets_data.keys())
        selected_category = st.selectbox("📂 选择单词书:", category_list)
        
        df_current = sheets_data[selected_category]
        total_words = len(df_current)
        learned_in_cat = 0
        all_words_in_cat = df_current['单词 (Word)'].tolist()
        for w in all_words_in_cat:
            if w in progress and progress[w]['level'] > 0:
                learned_in_cat += 1
                
        st.caption(f"当前分类进度: {learned_in_cat}/{total_words}")
        st.progress(learned_in_cat / total_words if total_words > 0 else 0)

        st.divider()
        menu = st.radio("功能模式", ["📖 开始学习", "🔄 智能复习", "📊 数据看板"])

    if menu == "📊 数据看板":
        st.title(f"你好, {current_user} 👋")
        st.markdown(f"你正在学习: **{selected_category}**")
        st.info(f"该分类下共有 {total_words} 个单词。")
        st.bar_chart({"已学": learned_in_cat, "未学": total_words - learned_in_cat})

    elif menu == "📖 开始学习":
        all_words = df_current['单词 (Word)'].tolist()
        new_words = [w for w in all_words if w not in progress]
        
        if not new_words:
            st.success(f"太棒了！[{selected_category}] 里的词你全背完了！")
            st.balloons()
        else:
            current_word_str = new_words[0]
            row = df_current[df_current['单词 (Word)'] == current_word_str].iloc[0]
            
            st.title(f"{row['单词 (Word)']}")
            st.caption(f"📚 {selected_category}")
            st.text(f"音标: {row['音标 (Phonetic)']}")
            
            if st.button("🔊 朗读"):
                play_audio(current_word_str)
                
            with st.expander("👁️ 记忆卡片", expanded=True):
                st.subheader(row['中文 (Meaning)'])
                m_type = st.radio("模式:", ["🧠 脑洞联想", "🌲 词源逻辑"], horizontal=True)
                
                if m_type == "🧠 脑洞联想":
                    st.info(f"💡 {row['脑洞联想 (Mnemonic)']}")
                    img = row.get('语境图描述 (ImagePrompt)', '')
                    if str(img).startswith('http'):
                        st.image(img)
                else:
                    st.info(f"📘 {row['词源/逻辑 (Etymology)']}")

            st.markdown("---")
            s1 = row.get('例句1 (Sentence1)', '')
            cn1 = row.get('例句1中文 (CN1)', '')
            if s1:
                st.markdown(f"**1. {s1}**")
                st.caption(f"{cn1}")
                if st.button("🔊 听例句"): play_audio(str(s1))
            
            st.markdown("---")
            if st.button("✅ 学会了 (存入云端)", type="primary"):
                progress[current_word_str] = {"level": 1, "next_review": get_next_review_time(1)}
                save_user_progress(current_user, progress)
                st.rerun()

    elif menu == "🔄 智能复习":
        due_list = [w for w in progress if progress[w]['next_review'] < time.time()]
        
        if not due_list:
            st.success("目前没有需要复习的单词！")
        else:
            word = due_list[0]
            word_row = None
            found_sheet = ""
            for sheet_name, df in sheets_data.items():
                if word in df['单词 (Word)'].values:
                    word_row = df[df['单词 (Word)'] == word].iloc[0]
                    found_sheet = sheet_name
                    break
            
            if word_row is None:
                del progress[word]
                save_user_progress(current_user, progress)
                st.rerun()
            else:
                st.header(f"复习: {word}")
                st.caption(f"来源: {found_sheet}")
                with st.expander("查看提示"):
                    st.info(word_row['脑洞联想 (Mnemonic)'])
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("❌ 忘了"):
                        progress[word]['level'] = 1
                        progress[word]['next_review'] = get_next_review_time(1)
                        save_user_progress(current_user, progress)
                        st.rerun()
                with c2:
                    if st.button("✅ 记得"):
                        progress[word]['level'] += 1
                        progress[word]['next_review'] = get_next_review_time(progress[word]['level'])
                        save_user_progress(current_user, progress)
                        st.balloons()
                        time.sleep(1)
                        st.rerun()
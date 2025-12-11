import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import time
import datetime
import json

# --- 1. CSS 暴力美学 (强制深色字体) ---
def local_css():
    st.markdown("""
    <style>
    /* 🔴 核心修复：暴力强制所有文字颜色为深灰，防止白底白字 */
    html, body, [class*="css"] {
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
        color: #333333 !important; /* 强制深灰色字体 */
    }
    
    /* 修复输入框、下拉菜单的标签文字 */
    .stTextInput label, .stSelectbox label, .stNumberInput label, .stTextArea label {
        color: #111827 !important;
        font-weight: bold !important;
    }
    
    /* 修复侧边栏文字 */
    [data-testid="stSidebar"] * {
        color: #1F2937 !important;
    }
    
    /* 修复主背景色 */
    .stApp { background-color: #F3F4F6; }
    
    /* 隐藏 Streamlit 默认的红线头 */
    header { visibility: hidden; }
    
    /* === 卡片通用样式 === */
    .nav-card {
        background: white; padding: 20px; border-radius: 15px;
        border: 1px solid #ddd; text-align: center; cursor: pointer;
        transition: 0.3s; height: 100%;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    .nav-card:hover { border-color: #4F46E5; transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    
    /* 单词卡片 (学习页/复习页) */
    .word-card {
        background: #FFFFFF; /* 纯白背景 */
        border-radius: 20px; padding: 40px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08); 
        text-align: center; border: 1px solid #E5E7EB; 
        margin-bottom: 25px;
    }
    
    /* 单词大标题 */
    .big-word { 
        font-size: 3.5rem !important; 
        font-weight: 900 !important; 
        color: #111827 !important; /* 极深黑 */
        margin: 0 !important; 
    }
    
    /* 含义框 (绿色背景+深绿字) */
    .meaning-box {
        background: #ECFDF5; border-left: 5px solid #10B981;
        padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px;
    }
    .meaning-text { 
        color: #065F46 !important; /* 深绿色字体 */
        font-size: 1.2rem !important;
        font-weight: bold;
    }
    
    /* 脑洞框 (紫色背景+深紫字) */
    .brain-box {
        background: #EEF2FF; border-left: 5px solid #6366F1;
        padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px;
    }
    .brain-text { 
        color: #4338CA !important; /* 深紫色字体 */
        font-size: 1.1rem !important;
    }
    
    /* 例句框 */
    .sent-box {
        background: white; border-bottom: 1px solid #eee;
        padding: 12px 0; text-align: left;
    }
    .sent-en { color: #1F2937 !important; font-weight: bold; font-size: 1.1rem; }
    .sent-cn { color: #6B7280 !important; font-size: 0.95rem; }

    /* 按钮文字 */
    button p { color: inherit !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库连接 ---
@st.cache_resource
def init_mongo():
    try: return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

def get_db():
    client = init_mongo()
    if client is None: return None
    return client.luna_vocab_db

# --- 3. AI 连接 ---
@st.cache_resource
def get_ai_client():
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

# --- 4. 智能查词 (带余额保护) ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    try:
        cached = db.library.find_one({"word": word.lower().strip()})
        if cached: return cached
    except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            prompt = f"""生成单词 "{word}" 的JSON: {{"word":"{word}","phonetic":"音标","meaning":"中文含义","category":"分类(如商务/生活)","mnemonic":"中文谐音记忆","sentences":[{{"en":"英文句","cn":"中文译"}}]}}"""
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].lower().strip()
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            # 这里的 print 会显示在后台日志里，方便排查
            print(f"AI Error: {e}")
            return None
    return None

def batch_gen(topic):
    ai = get_ai_client()
    if not ai: return []
    try:
        prompt = f"列出10个关于'{topic}'的核心英文单词，只返回JSON数组 ['word1', 'word2']"
        resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        if isinstance(data, dict): return list(data.values())[0]
        return data if isinstance(data, list) else []
    except: return []

# --- 5. 辅助工具 ---
def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h
def play_audio(text):
    try:
        sound = BytesIO(); tts = gTTS(text=text, lang='en'); tts.write_to_fp(sound)
        st.audio(sound, format='audio/mp3', start_time=0)
    except: pass
def get_next_time(lvl):
    intervals = [0, 86400, 259200, 604800, 1296000, 2592000]
    return time.time() + (intervals[lvl] if lvl < len(intervals) else 2592000)

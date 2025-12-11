import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import datetime
import json

# --- 1. CSS 强力漂白 (V23.0) ---
def local_css():
    st.markdown("""
    <style>
    /* === 全局强制：亮色模式 === */
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6 !important; }
    header { visibility: hidden; }
    
    /* 强制所有文字颜色 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li {
        color: #111827 !important;
        font-family: sans-serif;
    }

    /* === 🔴 核心修复：彻底漂白输入框背景 === */
    /* 针对所有文本输入框的外壳 */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 8px !important;
    }
    /* 针对输入框里面的文字区域 */
    input[type="text"], input[type="password"] {
        background-color: #FFFFFF !important;
        color: #111827 !important;
    }
    
    /* === 修复下拉菜单 === */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        color: #111827 !important;
    }
    /* 下拉选项列表 */
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[role="option"] { color: #111827 !important; }
    li[role="option"]:hover { background-color: #E0E7FF !important; }

    /* === 修复按钮 (告别全黑按钮) === */
    /* 主按钮 (Primary) - 比如“登录”、“生成” */
    button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
    }
    button[kind="primary"]:hover {
        background-color: #4338CA !important;
    }
    
    /* 次级按钮 (Secondary) - 比如“退出”、“返回” */
    button[kind="secondaryFormSubmit"], button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #1F2937 !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 8px !important;
    }
    button[kind="secondary"]:hover {
        border-color: #4F46E5 !important;
        color: #4F46E5 !important;
    }

    /* === 卡片样式 === */
    .nav-card {
        background: white !important; padding: 24px; border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; cursor: pointer; transition: all 0.2s; height: 100%;
    }
    .nav-card:hover { transform: translateY(-5px); border-color: #4F46E5; }
    
    .word-card {
        background: white !important; padding: 30px; border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08); text-align: center;
        border: 1px solid #E5E7EB; margin-bottom: 20px;
    }
    
    .meaning-box { background: #ECFDF5 !important; border-left: 5px solid #10B981 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left; }
    .brain-box { background: #EEF2FF !important; border-left: 5px solid #6366F1 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left; }
    .tag-pill { background: #E5E7EB !important; color: #374151 !important; padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; font-weight: 600; margin: 5px; display: inline-block;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库 ---
@st.cache_resource
def init_mongo():
    try: return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

def get_db():
    client = init_mongo()
    if client is None: return None
    return client.luna_vocab_db

# --- 3. AI ---
@st.cache_resource
def get_ai_client():
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

# --- 4. 智能查词 ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    query = word.lower().strip()
    # 查缓存
    try:
        cached = db.library.find_one({"word": query})
        # 如果缓存数据完整，直接返回
        if cached and 'roots' in cached and 'collocations' in cached:
            return cached
    except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            # Prompt 保持最新：要求词根、英文搭配
            prompt = f"""
            Generate JSON for English word "{query}".
            Strict Schema:
            1. "word": "{query}"
            2. "phonetic": IPA
            3. "meaning": Chinese meaning (Business preferred)
            4. "roots": Chinese Etymology (e.g. re-回 + turn-转)
            5. "collocations": List of 3 **English phrases**
            6. "mnemonic": Chinese mnemonic
            7. "category": Classification
            8. "sentences": List of 3 sentences ({{ "en": "...", "cn": "..." }})
            Return JSON only.
            """
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            data['word'] = query
            data['created_at'] = datetime.datetime.now()
            
            db.library.update_one({"word": query}, {"$set": data}, upsert=True)
            return data
        except: return None
    return None

def batch_gen(topic):
    ai = get_ai_client()
    if not ai: return []
    try:
        prompt = f"List 10 English words about '{topic}', return JSON array ['word1', 'word2']"
        resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        if isinstance(data, dict): return list(data.values())[0]
        return data if isinstance(data, list) else []
    except: return []

# --- 5. 辅助 ---
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

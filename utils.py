import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import datetime
import json

# --- 1. CSS 强力纠色 (防止隐形文字) ---
def local_css():
    st.markdown("""
    <style>
    /* 1. 强制全局所有文字为深黑色，无视系统主题 */
    html, body, [class*="css"], .stApp, p, h1, h2, h3, div, span, label, li, button {
        color: #111827 !important; 
        font-family: sans-serif;
    }
    
    /* 2. 强制背景为浅灰 */
    .stApp { background-color: #F3F4F6 !important; }
    
    /* 3. 修复输入框和下拉菜单看不见的问题 */
    .stTextInput input, .stSelectbox div, .stNumberInput input {
        color: #111827 !important;
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
    }
    /* 下拉菜单选项颜色 */
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[role="option"] { color: #111827 !important; }
    
    /* 4. 卡片样式 */
    .word-card {
        background: white !important; 
        padding: 30px; border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; margin-bottom: 20px;
    }
    
    /* 5. 导航卡片 */
    .nav-card {
        background: white !important; padding: 20px; border-radius: 15px;
        border: 1px solid #ddd; text-align: center; cursor: pointer;
        transition: 0.3s; height: 100%;
    }
    .nav-card:hover { border-color: #4F46E5; transform: translateY(-5px); }
    
    /* 6. 详情模块颜色 */
    .meaning-box { background: #ECFDF5 !important; border-left: 5px solid #10B981 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left;}
    .brain-box { background: #EEF2FF !important; border-left: 5px solid #6366F1 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left;}
    .roots-box { background: #FFF7ED !important; border-left: 5px solid #F97316 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left;}
    
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

# --- 3. AI 连接 ---
@st.cache_resource
def get_ai_client():
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

# --- 4. 智能查词 (Prompt 升级：英文组词+词根) ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    query = word.lower().strip()
    cached = db.library.find_one({"word": query})
    
    # 如果缓存缺失重要字段，强制重查
    if cached and 'roots' in cached and 'collocations' in cached:
        return cached
    
    ai = get_ai_client()
    if ai:
        try:
            # 🔥 这里的 Prompt 专门针对你的需求进行了修改
            prompt = f"""
            Generate JSON for English word "{query}".
            Strict requirements:
            1. "word": "{query}"
            2. "phonetic": IPA symbol
            3. "meaning": Chinese meaning (Business context preferred)
            4. "roots": Explain etymology/roots in Chinese (e.g. 'bene-好 + fit-做')
            5. "collocations": List of 3 common **English phrases** (Must be English! e.g. 'heavy rain', 'sign a contract')
            6. "mnemonic": Chinese mnemonic
            7. "category": Classification (Business/Daily/Tech)
            8. "sentences": List of 3 example sentences. Each object has "en" and "cn".
            
            Return JSON only.
            """
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            data['word'] = query
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": query}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            print(e)
            return None
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

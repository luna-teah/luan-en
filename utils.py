import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import datetime
import json

# --- 1. CSS 动态美化 (支持自定义颜色) ---
def set_style(text_color="#1F2937", bg_color="#F3F4F6"):
    st.markdown(f"""
    <style>
    /* 强制全局字体颜色 (用户自定义) */
    html, body, [class*="css"], p, h1, h2, h3, div, span, label, li {{
        color: {text_color} !important;
        font-family: 'Helvetica Neue', sans-serif;
    }}
    
    /* 背景颜色 */
    .stApp {{ background-color: {bg_color}; }}
    
    /* 修复输入框看不清 */
    .stTextInput input, .stSelectbox div, .stNumberInput input {{
        color: {text_color} !important;
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB;
    }}
    
    /* --- 卡片样式 (防止缩进导致的乱码) --- */
    .word-card {{
        background: white; padding: 30px; border-radius: 20px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; margin-bottom: 20px;
    }}
    
    /* 模块容器 */
    .info-container {{
        text-align: left; margin-top: 15px; padding: 15px; border-radius: 10px;
        font-size: 1.1rem; line-height: 1.6;
    }}
    
    .box-meaning {{ background: #ECFDF5; border-left: 5px solid #10B981; color: #065F46 !important; }}
    .box-roots {{ background: #FFF7ED; border-left: 5px solid #F97316; color: #9A3412 !important; }}
    .box-colloc {{ background: #F0F9FF; border-left: 5px solid #0EA5E9; color: #0C4A6E !important; }}
    .box-mnem {{ background: #EEF2FF; border-left: 5px solid #6366F1; color: #4338CA !important; }}
    
    .label-head {{ font-weight: 800; font-size: 0.8rem; opacity: 0.8; text-transform: uppercase; display: block; margin-bottom: 5px; }}
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

# --- 4. 智能查词 (Prompt 升级) ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    query = word.lower().strip()
    cached = db.library.find_one({"word": query})
    
    # 如果缓存里缺字段，强制重新生成
    if cached and 'collocations' in cached and 'roots' in cached: 
        return cached
    
    ai = get_ai_client()
    if ai:
        try:
            # 🔥 核心升级：要求英文搭配、词根、造句
            prompt = f"""
            Generate a JSON for English word "{query}".
            Fields:
            1. "word": "{query}"
            2. "phonetic": IPA
            3. "meaning": Chinese meaning (Business context)
            4. "roots": Etymology/Roots explanation in Chinese (e.g. 'bene-好 + fit-做')
            5. "collocations": List of 3 common **English phrases** (e.g. ['sign a contract', 'heavy rain'])
            6. "mnemonic": Creative Chinese mnemonic
            7. "category": Category
            8. "sentences": List of 3 sentences (1 simple, 1 business, 1 complex). Each has "en" and "cn".
            
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

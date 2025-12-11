import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import time
import datetime
import json

# --- 1. CSS 修复 (重点修复下拉菜单看不清) ---
def local_css():
    st.markdown("""
    <style>
    /* 全局强制深色字体 */
    .stApp, p, h1, h2, h3, h4, div, span, label, li { 
        color: #111827 !important; 
        font-family: 'Helvetica Neue', sans-serif;
    }
    
    /* 强制背景灰白 */
    .stApp { background-color: #F3F4F6; }
    
    /* --- 🔴 重点修复：下拉菜单和输入框看不清的问题 --- */
    /* 输入框背景白，字黑 */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border-color: #D1D5DB !important;
    }
    /* 下拉选项菜单的背景和文字 */
    ul[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    li[role="option"] {
        color: #111827 !important;
    }
    /* 选中时的颜色 */
    li[role="option"][aria-selected="true"] {
        background-color: #E0E7FF !important;
    }
    /* ----------------------------------------------- */

    /* 卡片样式 */
    .word-card {
        background: white; border-radius: 20px; padding: 35px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; margin-bottom: 20px;
    }
    
    /* 模块框 */
    .section-box {
        text-align: left; margin-top: 15px; padding: 15px; border-radius: 10px;
        font-size: 1rem; line-height: 1.6;
    }
    .box-meaning { background: #ECFDF5; border-left: 5px solid #10B981; color: #065F46 !important; }
    .box-roots { background: #FFF7ED; border-left: 5px solid #F97316; color: #9A3412 !important; }
    .box-colloc { background: #F0F9FF; border-left: 5px solid #0EA5E9; color: #0C4A6E !important; }
    .box-mnem { background: #EEF2FF; border-left: 5px solid #6366F1; color: #4338CA !important; }
    
    .label-title { font-weight: 800; font-size: 0.8rem; opacity: 0.7; text-transform: uppercase; margin-bottom: 5px; display:block;}
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

# --- 4. 智能查词 (升级版：加入词根、英文搭配) ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    query = word.lower().strip()
    cached = db.library.find_one({"word": query})
    
    # 强制检查新字段，如果旧缓存没有词根，则重新生成
    if cached and 'roots' in cached and 'collocations' in cached: 
        return cached
    
    ai = get_ai_client()
    if ai:
        try:
            # 🔥 Prompt 升级：要求词根、英文搭配
            prompt = f"""
            Generate a detailed JSON for English word "{query}".
            Fields required:
            1. "word": "{query}"
            2. "phonetic": IPA symbol
            3. "meaning": Chinese meaning (Business/Trade context first)
            4. "roots": Etymology/Roots explanation (in Chinese, e.g. 're-回 + turn-转')
            5. "collocations": List of 3-4 common ENGLISH phrases (e.g. ['sign a contract', 'breach of contract'])
            6. "mnemonic": Creative Chinese mnemonic (Brain association)
            7. "category": Category (Business/Daily/Tech)
            8. "sentences": List of 3 sentences (1 simple, 1 business, 1 complex). Each with "en" and "cn".
            
            Return ONLY JSON.
            """
            resp = ai.chat.completions.create(
                model="deepseek-chat", 
                messages=[{"role":"user","content":prompt}], 
                temperature=1.1, 
                response_format={"type":"json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            data['word'] = query
            data['created_at'] = datetime.datetime.now()
            
            # 更新数据库 (upsert)
            db.library.update_one({"word": query}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            return None
    return None

def batch_gen(topic):
    ai = get_ai_client()
    if not ai: return []
    try:
        prompt = f"List 10 core English words about '{topic}', return JSON array ['word1', 'word2']"
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

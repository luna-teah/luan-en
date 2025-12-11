import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import datetime
import time
import json
import re

def local_css():
    st.markdown("""
    <style>
    /* 强制全局亮色模式 */
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6 !important; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    
    /* 强制所有文字黑色 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li, button { 
        color: #000000 !important; 
        font-family: sans-serif; 
    }
    
    /* 修复输入框变黑的问题 */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #9CA3AF !important;
        border-radius: 5px !important;
    }
    input {
        color: #000000 !important;
        background-color: #FFFFFF !important;
    }
    
    /* 修复下拉菜单变黑的问题 */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #9CA3AF !important;
    }
    ul[data-baseweb="menu"] {
        background-color: #FFFFFF !important;
    }
    li[role="option"] {
        color: #000000 !important;
        background-color: #FFFFFF !important;
    }
    li[role="option"]:hover {
        background-color: #E5E7EB !important;
    }

    /* 按钮样式 */
    button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #9CA3AF !important;
    }

    /* 卡片样式 */
    .word-card {
        background-color: #FFFFFF !important;
        padding: 30px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        text-align: center;
        margin-bottom: 20px;
        border: 1px solid #E5E7EB;
    }
    
    .info-box {
        background-color: #FFFFFF !important;
        border-left: 5px solid #4F46E5;
        padding: 15px;
        margin-top: 10px;
        text-align: left;
        border: 1px solid #E5E7EB;
    }
    
    .tag-span {
        background-color: #E5E7EB !important;
        color: #000000 !important;
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 0.8rem;
        margin: 5px;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)

@st.cache_resource
def init_mongo():
    try: return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

def get_db():
    client = init_mongo()
    if client is None: return None
    return client.luna_vocab_db

@st.cache_resource
def get_ai_client():
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

def smart_fetch(word_input):
    db = get_db()
    if db is None: return None
    
    raw_input = word_input.strip()
    
    # 检测中文，如果是中文直接跳过查库，走AI翻译
    is_chinese = any(ord(c) > 128 for c in raw_input)
    
    if not is_chinese:
        query = raw_input.lower()
        try:
            cached = db.library.find_one({"word": query})
            # 检查字段是否完整
            if cached and 'roots' in cached and 'collocations' in cached:
                return cached
        except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            # 强制要求: 英文单词, 简单造句, 词根
            prompt = f"""
            Task: Generate JSON for "{raw_input}".
            
            1. If input is Chinese, translate to English first.
            2. "word" field MUST be English.
            3. "roots": Root explanation in Chinese.
            4. "collocations": 3 English phrases.
            5. "sentences": 3 sentences (Child level -> Daily level -> Business level).
            
            Format:
            {{
                "word": "EnglishWord",
                "phonetic": "IPA",
                "meaning": "Chinese Meaning",
                "roots": "Root explanation",
                "collocations": ["phrase1", "phrase2", "phrase3"],
                "mnemonic": "Memory trick",
                "category": "Category",
                "sentences": [
                    {{"en": "Simple sentence.", "cn": "Simple translation."}},
                    {{"en": "Daily sentence.", "cn": "Daily translation."}},
                    {{"en": "Business sentence.", "cn": "Business translation."}}
                ]
            }}
            """
            
            resp = ai.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role":"user","content":prompt}],
                response_format={"type":"json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            
            final_word = data['word'].strip()
            data['created_at'] = datetime.datetime.now()
            
            # 存入数据库
            db.library.update_one({"word": final_word.lower()}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            print(f"AI Error: {e}")
            return None
    return None

def batch_gen(topic):
    ai = get_ai_client()
    if not ai: return []
    try:
        prompt = f"List 10 simple English words about '{topic}' for beginners. Return JSON array of strings: ['word1', 'word2']"
        resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        if isinstance(data, dict):
            # 兼容处理 {'words': [...]}
            return list(data.values())[0]
        return data if isinstance(data, list) else []
    except: return []

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

def update_daily_activity(user_id):
    db = get_db()
    if db is None: return
    today_str = datetime.datetime.now().strftime("%Y-%m-%d")
    db.users.update_one({"_id": user_id}, {"$inc": {f"stats.{today_str}": 1}})

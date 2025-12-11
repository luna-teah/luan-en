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
import os

def local_css():
    st.markdown("""
    <style>
    /* 强制亮色背景 */
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6 !important; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    
    /* 全局文字深色 */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li, button { 
        color: #111827 !important; 
        font-family: sans-serif; 
    }
    
    /* 修复输入框变黑 */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 5px !important;
    }
    input {
        color: #111827 !important;
        background-color: #FFFFFF !important;
        caret-color: #000000 !important;
    }
    
    /* 修复下拉菜单 */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #D1D5DB !important;
    }
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[role="option"] { color: #111827 !important; background-color: #FFFFFF !important; }
    li[role="option"]:hover { background-color: #E0E7FF !important; }

    /* 按钮 */
    button[kind="primary"] {
        background-color: #4F46E5 !important;
        color: #FFFFFF !important;
        border: none !important;
    }
    button[kind="secondary"] {
        background-color: #FFFFFF !important;
        color: #111827 !important;
        border: 1px solid #D1D5DB !important;
    }

    /* 卡片 */
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
    is_chinese = any(ord(c) > 128 for c in raw_input)
    
    if not is_chinese:
        query = raw_input.lower()
        try:
            cached = db.library.find_one({"word": query})
            # 如果缓存有 sentences，直接用
            if cached and 'sentences' in cached: return cached
        except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            # 🔥 省钱核心：1句造句 + 1个搭配(带中文)
            prompt = f"""
            Task: Generate JSON for "{raw_input}".
            1. If input is Chinese, translate to English first.
            2. "word": English word.
            3. "meaning": Single string of Chinese meaning.
            4. "roots": Root explanation in Chinese.
            5. "collocations": List of 1 common phrase with Chinese translation (e.g. "go home (回家)").
            6. "mnemonic": Funny memory trick.
            7. "category": Category.
            8. "sentences": List of 1 very simple sentence (Child level).
            
            Format:
            {{
                "word": "EnglishWord",
                "phonetic": "IPA",
                "meaning": "Chinese Meaning",
                "roots": "Root explanation",
                "collocations": ["phrase (cn)"],
                "mnemonic": "Trick",
                "category": "Category",
                "sentences": [
                    {{"en": "Simple sentence.", "cn": "Translation."}}
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
            
            db.library.update_one({"word": final_word.lower()}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            return None
    return None

def batch_gen(topic):
    ai = get_ai_client()
    if not ai: return []
    try:
        prompt = f"List 10 simple English words about '{topic}' for beginners. Return JSON array: ['word1', 'word2']"
        resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        if isinstance(data, dict): return list(data.values())[0]
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

import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import time
import datetime
import json

# --- 1. CSS 美化 (全局控制颜值) ---
def local_css():
    st.markdown("""
    <style>
    /* 强制全局深色文字，防止白底白字 */
    h1, h2, h3, p, div, span, label, li { color: #1F2937 !important; font-family: sans-serif; }
    .stApp { background-color: #F3F4F6; }
    
    /* 卡片通用样式 */
    .nav-card {
        background: white; padding: 20px; border-radius: 15px;
        border: 1px solid #ddd; text-align: center; cursor: pointer;
        transition: 0.3s; height: 100%;
    }
    .nav-card:hover { border-color: #4F46E5; transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    
    .word-card {
        background: white; border-radius: 20px; padding: 30px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; margin-bottom: 20px;
    }
    
    .info-box { text-align: left; background: #F9FAFB; padding: 15px; border-radius: 8px; margin-top: 15px; }
    .brain-box { text-align: left; margin-top: 15px; background: #EEF2FF; padding: 15px; border-radius: 8px; border-left: 4px solid #4F46E5; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. 数据库连接 ---
@st.cache_resource
def init_mongo():
    try: return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

def get_db():
    client = init_mongo()
    return client.luna_vocab_db if client else None

# --- 3. AI 连接 ---
@st.cache_resource
def get_ai_client():
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

# --- 4. 智能查词核心逻辑 ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    cached = db.library.find_one({"word": word.lower().strip()})
    if cached: return cached
    
    ai = get_ai_client()
    if ai:
        try:
            prompt = f"""生成单词 "{word}" 的JSON: {{"word":"{word}","phonetic":"音标","meaning":"含义","category":"分类","mnemonic":"脑洞","sentences":[{{"en":"句","cn":"译"}}]}}"""
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].lower().strip()
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except: return None
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

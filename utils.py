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

# --- 1. CSS 样式 (保持 V23 强力漂白) ---
def local_css():
    st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6 !important; }
    header { visibility: hidden; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, li { 
        color: #111827 !important; font-family: sans-serif; 
    }
    
    div[data-baseweb="input"] { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; border-radius: 8px !important; }
    input { background-color: #FFFFFF !important; color: #111827 !important; }
    
    div[data-baseweb="select"] > div { background-color: #FFFFFF !important; border: 1px solid #D1D5DB !important; color: #111827 !important; }
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[role="option"] { color: #111827 !important; }
    li[role="option"]:hover { background-color: #E0E7FF !important; }

    button[kind="primary"] { background-color: #4F46E5 !important; color: white !important; border: none !important; border-radius: 8px !important; }
    button[kind="primary"]:hover { background-color: #4338CA !important; }
    button[kind="secondary"] { background-color: #FFFFFF !important; color: #1F2937 !important; border: 1px solid #D1D5DB !important; border-radius: 8px !important; }

    .word-card { background: white !important; padding: 30px; border-radius: 20px; box-shadow: 0 10px 25px rgba(0,0,0,0.08); text-align: center; border: 1px solid #E5E7EB; margin-bottom: 20px; }
    .meaning-box { background: #ECFDF5 !important; border-left: 5px solid #10B981 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left; }
    .roots-box { background: #FFF7ED !important; border-left: 5px solid #F97316 !important; padding: 15px; border-radius: 8px; margin-top: 15px; text-align: left; }
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

# --- 4. 智能查词 (🔥 核心升级：强制中译英) ---
def smart_fetch(word_input):
    db = get_db()
    if db is None: return None
    
    raw_input = word_input.strip()
    
    # 1. 如果输入的是中文（包含非ASCII字符），不要去查库，直接扔给AI翻译
    # 只有纯英文输入才去查库缓存
    if all(ord(c) < 128 for c in raw_input):
        query = raw_input.lower()
        try:
            cached = db.library.find_one({"word": query})
            if cached and 'sentences' in cached: return cached
        except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            # 🔥 Prompt 升级：先检测语言，如果是中文，先翻译成英文再生成
            prompt = f"""
            Analyze the input: "{raw_input}".
            
            **Step 1: Translation**
            - If the input is Chinese (e.g. '电子商务'), translate it to the most common English word (e.g. 'E-commerce').
            - If the input is English, use it as is.
            - **The "word" field in JSON MUST BE ENGLISH!**
            
            **Step 2: Generation**
            Generate JSON for that English word.
            
            Strict Requirements:
            1. "word": The English word (Capitalize first letter if noun).
            2. "phonetic": IPA
            3. "meaning": Chinese meaning (Simple & Business)
            4. "roots": Root explanation in Chinese
            5. "collocations": 3 common **English phrases**
            6. "mnemonic": Creative Chinese mnemonic
            7. "category": Classification
            8. "sentences": List of 3 sentences sorted by difficulty:
               - **Sentence 1 (Child Level)**: Extremely simple (max 8 words).
               - **Sentence 2 (Daily Level)**: Simple daily conversation.
               - **Sentence 3 (Business Level)**: Formal business context.
               Each object: {{ "en": "...", "cn": "..." }}
            
            Return JSON only.
            """
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            
            # 确保入库的是英文 (转小写存索引，但保留原词大小写)
            final_word = data['word']
            data['created_at'] = datetime.datetime.now()
            
            # 存入数据库 (使用英文作为主键)
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
        prompt = f"List 10 simple English words about '{topic}' for beginners, return JSON array ['word1', 'word2']"
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

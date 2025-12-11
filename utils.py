import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import datetime
import time
import json

def local_css():
    st.markdown("""
    <style>
    /* Force Light Mode */
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6 !important; }
    header { visibility: hidden; }
    
    /* Force Text Color */
    h1, h2, h3, h4, h5, h6, p, div, span, label, li, button { 
        color: #000000 !important; 
        font-family: sans-serif; 
    }
    
    /* Fix Input Fields (White Background) */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #9CA3AF !important;
        border-radius: 5px !important;
    }
    input {
        color: #000000 !important;
        background-color: #FFFFFF !important;
        caret-color: #000000 !important;
    }
    
    /* Fix Dropdowns */
    div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #9CA3AF !important;
    }
    ul[data-baseweb="menu"] { background-color: #FFFFFF !important; }
    li[role="option"] { color: #000000 !important; background-color: #FFFFFF !important; }
    li[role="option"]:hover { background-color: #E5E7EB !important; }

    /* Buttons */
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

    /* Cards */
    .word-card { background-color: #FFFFFF !important; padding: 30px; border-radius: 15px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); text-align: center; margin-bottom: 20px; border: 1px solid #E5E7EB; }
    .nav-card { background-color: #FFFFFF !important; padding: 20px; border-radius: 15px; border: 1px solid #E5E7EB; text-align: center; height: 100%; }
    .info-box { background-color: #FFFFFF !important; border-left: 5px solid #4F46E5; padding: 15px; margin-top: 10px; text-align: left; border: 1px solid #E5E7EB; }
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

def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    query = word.lower().strip()
    try:
        cached = db.library.find_one({"word": query})
        if cached and 'roots' in cached and 'sentences' in cached: return cached
    except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            prompt = f"""Generate JSON for English word "{query}". Strict JSON format only. Fields: word, phonetic, meaning (Chinese), roots (Chinese), collocations (3 English phrases), mnemonic (Chinese), category, sentences (3 objects with en, cn). Sentence 1 must be very simple."""
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
        prompt = f"List 10 simple English words about '{topic}' for beginners. JSON array of strings only: ['word1', 'word2']"
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

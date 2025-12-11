import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import time
import datetime
import json

def local_css():
    st.markdown("""
    <style>
    h1, h2, h3, p, div, span, label, li, button { color: #1F2937 !important; font-family: sans-serif; }
    .stApp { background-color: #F3F4F6; }
    .nav-card { background: white; padding: 20px; border-radius: 15px; border: 1px solid #ddd; text-align: center; height: 100%; transition:0.3s; }
    .nav-card:hover { border-color: #4F46E5; transform: translateY(-5px); box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    .word-card { background: white; border-radius: 20px; padding: 30px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); text-align: center; border: 1px solid #E5E7EB; margin-bottom: 20px; }
    .meaning-box { background: #ECFDF5; border-left: 5px solid #10B981; padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px; }
    .brain-box { background: #EEF2FF; border-left: 5px solid #6366F1; padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px; }
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
    
    try:
        cached = db.library.find_one({"word": word.lower().strip()})
        if cached: return cached
    except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            prompt = f"""Generate JSON for word "{word}": {{"word":"{word}","phonetic":"IPA","meaning":"Chinese Meaning (Business)","category":"Category","mnemonic":"Memory Trick","sentences":[{{"en":"sentence","cn":"translation"}}]}}"""
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].lower().strip()
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            print(e)
            return None
    return None

def batch_gen(topic):
    ai = get_ai_client()
    if not ai: return []
    try:
        prompt = f"List 10 core English words about '{topic}' as a JSON array ['word1', 'word2']"
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

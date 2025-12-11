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

# --- 1. CSS 样式 (保持 V29 纯净修复版) ---
def local_css():
    st.markdown("""
    <style>
    /* 全局强制亮色背景和深色文字 */
    [data-testid="stAppViewContainer"] { background-color: #F3F4F6 !important; }
    header { visibility: hidden; }
    h1, h2, h3, h4, h5, h6, p, div, span, label, li, button { 
        color: #111827 !important; 
        font-family: sans-serif; 
    }
    
    /* 修复输入框 */
    div[data-baseweb="input"] {
        background-color: #FFFFFF !important;
        border: 1px solid #D1D5DB !important;
        border-radius: 8px !important;
    }
    input {
        color: #111827 !important;
        background-color: #FFFFFF !important;
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
    button[kind="primary"] { background-color: #4F46E5 !important; color: white !important; border: none !important; }
    button[kind="secondary"] { background-color: #FFFFFF !important; color: #1F2937 !important; border: 1px solid #D1D5DB !important; }

    /* 卡片 */
    .word-card { background: white !important; padding: 30px; border-radius: 20px; box-shadow: 0 5px 15px rgba(0,0,0,0.05); text-align: center; margin-bottom: 20px; border: 1px solid #E5E7EB; }
    .meaning-box { background: #ECFDF5 !important; border-left: 5px solid #10B981 !important; padding: 15px; margin-top: 15px; text-align: left; }
    .roots-box { background: #FFF7ED !important; border-left: 5px solid #F97316 !important; padding: 15px; margin-top: 15px; text-align: left; }
    .brain-box { background: #EEF2FF !important; border-left: 5px solid #6366F1 !important; padding: 15px; margin-top: 15px; text-align: left; }
    .tag-pill { background: #E5E7EB !important; color: #374151 !important; padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; margin: 5px; display: inline-block; }
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

# --- 4. 智能查词 (V25 自动翻译+分级造句版) ---
def smart_fetch(word):
    db = get_db()
    if db is None: return None
    
    query = word.lower().strip()
    try:
        cached = db.library.find_one({"word": query})
        # 如果缓存有且完整，直接返回
        if cached and 'roots' in cached and 'sentences' in cached: return cached
    except: pass
    
    ai = get_ai_client()
    if ai:
        try:
            prompt = f"""
            Generate JSON for English word "{query}".
            Strict Requirements:
            1. "word": "{query}" (If Chinese, translate to English first).
            2. "phonetic": IPA.
            3. "meaning": Chinese meaning.
            4. "roots": Root explanation in Chinese.
            5. "collocations": 3 common English phrases.
            6. "mnemonic": Creative Chinese mnemonic (Homophone preferred).
            7. "category": Classification.
            8. "sentences": 3 sentences (Child -> Daily -> Business).
            
            Return JSON only.
            """
            resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].strip() # Ensure clean word
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": data['word'].lower()}, {"$set": data}, upsert=True)
            return data
        except: return None
    return None

# --- 🔥 5. 批量生成 (升级版：支持数量 + 去重) ---
def batch_gen(topic, count=10, exclude_list=[]):
    ai = get_ai_client()
    if not ai: return []
    
    # 截取一部分已存在的单词传给AI，防止Token超限
    # 把 exclude_list 拼成字符串，最多传 500 个字符的长度给 AI 做参考
    ex_str = ", ".join(exclude_list[:100]) 
    if len(exclude_list) > 100: ex_str += "..."
    
    try:
        prompt = f"""
        Task: List {count} simple English words about '{topic}'.
        Constraints:
        1. Return JSON array of strings: ["word1", "word2", ...].
        2. Do NOT include these words (already learned): {ex_str}.
        3. Words should be suitable for beginners/intermediate.
        """
        resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
        data = json.loads(resp.choices[0].message.content)
        
        # 兼容 { "words": [...] } 格式
        if isinstance(data, dict):
            # 取字典里第一个是列表的值
            for v in data.values():
                if isinstance(v, list): return v
            return []
        return data if isinstance(data, list) else []
    except Exception as e:
        print(e)
        return []

# --- 6. 辅助工具 ---
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

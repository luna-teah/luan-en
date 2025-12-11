import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import time
import datetime
import json

# --- 1. 连接数据库 ---
@st.cache_resource
def init_mongo():
    try:
        # 使用 st.secrets 读取密码
        return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

def get_db():
    client = init_mongo()
    return client.luna_vocab_db if client else None

# --- 2. 连接 AI ---
@st.cache_resource
def get_ai_client():
    try:
        return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

# --- 3. 核心：智能查词 (带错误保护) ---
def smart_fetch_word(word_input):
    db = get_db()
    if db is None: return None
    
    query = word_input.strip().lower()
    # 查缓存
    cached = db.library.find_one({"word": query})
    if cached: return cached
    
    # AI 生成
    ai_client = get_ai_client()
    if ai_client:
        try:
            prompt = f"""
            生成单词 "{query}" 的JSON数据 (严格JSON格式):
            {{
                "word": "{query}", 
                "phonetic": "音标", 
                "meaning": "中文含义(商务优先)",
                "category": "分类(如:商务/生活)", 
                "mnemonic": "好记的中文脑洞记忆法",
                "sentences": [{{"en": "英文句", "cn": "中文翻译"}}] (5句)
            }}
            """
            resp = ai_client.chat.completions.create(
                model="deepseek-chat", 
                messages=[{"role":"user","content":prompt}], 
                temperature=1.1, 
                response_format={"type":"json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            data['word'] = query # 确保主键一致
            data['created_at'] = datetime.datetime.now()
            
            # 存入库
            db.library.update_one({"word": query}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            print(f"AI Error: {e}")
            # 返回一个基础兜底数据，防止报错
            return {
                "word": query, "phonetic": "...", "meaning": "AI余额不足或超时，请手动补充",
                "category": "未分类", "mnemonic": "", "sentences": []
            }
    return None

# --- 4. CSS 美化 (修复乱码的核心) ---
def local_css():
    st.markdown("""
    <style>
    /* 强制全局文字颜色 */
    .stApp, p, h1, h2, h3, div, span, label { color: #1F2937 !important; }
    
    /* 卡片容器 */
    .word-card {
        background: white; border-radius: 20px; 
        box-shadow: 0 10px 25px rgba(0,0,0,0.05); 
        padding: 30px; margin-bottom: 20px; border: 1px solid #E5E7EB;
        text-align: center;
    }
    
    /* 单词大标题 */
    .big-word { 
        font-size: 3.5rem !important; font-weight: 800 !important; 
        color: #4F46E5 !important; margin: 0 !important; 
    }
    
    /* 释义框 */
    .meaning-box {
        background: #ECFDF5; border-left: 5px solid #10B981;
        padding: 15px; text-align: left; border-radius: 8px; margin-top: 20px;
    }
    .meaning-text { font-size: 1.2rem !important; color: #065F46 !important; font-weight: bold; }
    
    /* 脑洞框 */
    .brain-box {
        background: #EEF2FF; border-left: 5px solid #6366F1;
        padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px;
    }
    .brain-text { font-size: 1.1rem !important; color: #4338CA !important; }
    
    /* 导航卡片 */
    .nav-card {
        background: white; padding: 20px; border-radius: 15px;
        border: 1px solid #ddd; text-align: center; cursor: pointer;
        transition: 0.3s;
    }
    .nav-card:hover { border-color: #4F46E5; transform: translateY(-5px); }
    </style>
    """, unsafe_allow_html=True)

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

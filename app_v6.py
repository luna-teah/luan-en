import streamlit as st
import pandas as pd
import time
import datetime
import json
import random
import hashlib  # ✅ 补上了这个关键工具！
import os       # ✅ 补上了操作系统工具
from gtts import gTTS
from io import BytesIO
import pymongo
from openai import OpenAI

# --- 0. 全局配置 & 页面初始化 ---
st.set_page_config(page_title="Luna Pro V14", page_icon="💎", layout="centered")

# 强制生成浅色配置文件
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#58cc02"\nbackgroundColor="#f7f9fb"\nsecondaryBackgroundColor="#ffffff"\ntextColor="#2d3436"\nfont="sans serif"\n')

# --- 1. 🎨 UI/UX 美学重构 (CSS) ---
def local_css():
    st.markdown("""
    <style>
    header {visibility: hidden;}
    .block-container {padding-top: 2rem; max-width: 800px;}
    
    .word-card {
        background: white;
        border-radius: 20px;
        box-shadow: 0 8px 24px rgba(149, 157, 165, 0.1);
        padding: 30px;
        margin-bottom: 20px;
        border: 1px solid #edf2f7;
        text-align: center;
        transition: all 0.3s ease;
    }
    .word-card:hover { transform: translateY(-3px); box-shadow: 0 12px 28px rgba(149, 157, 165, 0.15); }

    .big-word { font-size: 3.2rem; font-weight: 800; color: #2d3436; margin-bottom: 0px; letter-spacing: -1px; }
    .phonetic { font-family: 'Georgia', serif; color: #636e72; font-size: 1.2rem; margin-bottom: 15px; font-style: italic; }
    
    .meaning-box { 
        background: #f0fdf4; border-left: 5px solid #58cc02; 
        padding: 15px; border-radius: 8px; margin: 15px 0; text-align: left;
    }
    .meaning-text { font-size: 1.2rem; color: #14532d; font-weight: 600; }

    .brain-capsule {
        background: linear-gradient(135deg, #6c5ce7 0%, #a29bfe 100%);
        color: white; padding: 15px; border-radius: 12px;
        margin: 15px 0; text-align: left; position: relative;
        box-shadow: 0 4px 12px rgba(108, 92, 231, 0.3);
    }
    .brain-tag { font-size: 0.8rem; opacity: 0.8; text-transform: uppercase; font-weight: bold; display: block; margin-bottom: 5px; }
    .brain-text { font-size: 1.1rem; line-height: 1.5; font-weight: 500; }

    .sent-row {
        background: white; border-bottom: 1px solid #f1f2f6;
        padding: 12px 5px; text-align: left;
    }
    .sent-en { font-size: 1.05rem; color: #2d3436; font-weight: 500; margin-bottom: 4px; display: block; }
    .sent-cn { font-size: 0.9rem; color: #b2bec3; }
    
    .tag-cloud { display: flex; gap: 8px; justify-content: center; flex-wrap: wrap; margin-top: 15px; }
    .tag-pill {
        background: #f1f2f6; color: #636e72; padding: 4px 12px;
        border-radius: 20px; font-size: 0.85rem; font-weight: 600;
    }
    
    .review-btn-container { display: flex; gap: 10px; justify-content: center; margin-top: 20px; }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. 数据库与AI连接 ---
@st.cache_resource
def init_mongo():
    try: return pymongo.MongoClient(st.secrets["mongo"]["connection_string"])
    except: return None

client = init_mongo()
def get_db(): return client.luna_vocab_db if client else None

@st.cache_resource
def get_ai_client():
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url"])
    except: return None

ai_client = get_ai_client()

# --- 3. 核心逻辑：智能数据获取 ---
def smart_fetch_word_data(word):
    db = get_db()
    if not db: return None
    
    cached_word = db.library.find_one({"word": word.lower().strip()})
    
    if cached_word:
        return cached_word
    
    if ai_client:
        prompt = f"""
        请生成单词 "{word}" 的学习卡片 JSON 数据。
        要求：
        1. phonetic: 音标
        2. meaning: 中文含义(外贸/商务场景优先)
        3. mnemonic: 一个极其好记、搞笑的"谐音梗"或"脑洞"记忆法(中文)
        4. synonyms: 3个近义词(数组)
        5. antonyms: 3个反义词(数组)
        6. sentences: 5个例句数组，包含 {{ "en": "英文句", "cn": "中文翻译", "level": "难度1-5" }}
           - L1: 简单定义/短语
           - L2: 日常生活
           - L3: 商务沟通
           - L4: 进阶/合同
           - L5: 习语/高难
        
        只返回纯JSON。
        """
        try:
            response = ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.2,
                response_format={ "type": "json_object" }
            )
            data = json.loads(response.choices[0].message.content)
            data['word'] = word.lower().strip()
            data['created_at'] = datetime.datetime.now()
            
            db.library.insert_one(data)
            return data
        except Exception as e:
            st.error(f"AI 生成失败: {e}")
            return None
    return None

# --- 4. 辅助功能 ---
def play_audio(text):
    try:
        sound = BytesIO()
        tts = gTTS(text=text, lang='en')
        tts.write_to_fp(sound)
        st.audio(sound, format='audio/mp3', start_time=0)
    except: pass

def make_hashes(p): return hashlib.sha256(str.encode(p)).hexdigest()
def check_hashes(p, h): return make_hashes(p) == h

def get_next_review_time(level):
    intervals = [0, 86400, 259200, 604800, 1296000, 2592000]
    sec = intervals[level] if level < len(intervals) else 2592000
    return time.time() + sec

# --- 5. 登录系统 ---
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = ''

def login_page():
    st.markdown("<br><br><h1 style='text-align: center; color: #58cc02;'>💎 Luna Pro</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #aaa;'>外贸英语 · 众筹词库 · 智能记忆</p>", unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["登录", "注册"])
    db = get_db()
    
    with tab1:
        u = st.text_input("用户名", key="l_u")
        p = st.text_input("密码", type="password", key="l_p")
        if st.button("🚀 进入学习", use_container_width=True, type="primary"):
            if db is not None:
                user = db.users.find_one({"_id": u})
                if user and check_hashes(p, user['password']):
                    st.session_state['logged_in'] = True
                    st.session_state['username'] = u
                    st.rerun()
                else: st.error("账号或密码错误")
            else: st.error("数据库连接失败")
            
    with tab2:
        nu = st.text_input("新用户名", key="r_u")
        np = st.text_input("设置密码", type="password", key="r_p")
        if st.button("✨ 注册新账号", use_container_width=True):
            if db is not None:
                if db.users.find_one({"_id": nu}): st.warning("用户名已存在")
                else:
                    db.users.insert_one({
                        "_id": nu, "password": make_hashes(np), 
                        "progress": {},
                        "stats": {"streak": 0, "last_active": ""}
                    })
                    st.success("注册成功！请登录。")

# --- 6. 主程序逻辑 ---
if not st.session_state['logged_in']:
    login_page()
else:
    username = st.session_state['username']
    db = get_db()
    
    with st.sidebar:
        st.title(f"Hi, {username}")
        menu = st.radio("导航", ["🔎 极速查词", "🧠 沉浸复习", "📊 数据中心"])
        st.divider()
        if st.button("退出登录"):
            st.session_state['logged_in'] = False
            st.rerun()

    if menu == "🔎 极速查词":
        st.markdown("## 🔎 极速查词")
        word_input = st.text_input("输入单词回车 (支持中文/英文)", placeholder="例如: negotiation", key="search_box")
        
        if word_input:
            with st.spinner("🚀 正在云端检索 (如有缓存将秒开)..."):
                data = smart_fetch_word_data(word_input)
            
            if data:
                st.markdown(f"""
                <div class="word-card">
                    <p class="big-word">{data['word']}</p>
                    <p class="phonetic">/{data.get('phonetic', '...')}/</p>
                    <div class="tag-cloud">
                        {' '.join([f'<span class="tag-pill">🔗 {s}</span>' for s in data.get('synonyms', [])[:3]])}
                        {' '.join([f'<span class="tag-pill">⚡ {a}</span>' for a in data.get('antonyms', [])[:3]])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("🔊 朗读发音", use_container_width=True):
                    play_audio(data['word'])

                st.markdown(f"""
                <div class="meaning-box">
                    <span class="meaning-text">{data.get('meaning', '')}</span>
                </div>
                """, unsafe_allow_html=True)
                
                if data.get('mnemonic'):
                    st.markdown(f"""
                    <div class="brain-capsule">
                        <span class="brain-tag">🧠 脑洞记忆</span>
                        <span class="brain-text">{data['mnemonic']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("### 📚 场景例句")
                for sent in data.get('sentences', []):
                    st.markdown(f"""
                    <div class="sent-row">
                        <span class="sent-en">{sent['en']}</span>
                        <span class="sent-cn">{sent['cn']}</span>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.markdown("<br>", unsafe_allow_html=True)
                
                if st.button("⭐ 加入我的复习计划", type="primary", use_container_width=True):
                    db.users.update_one(
                        {"_id": username},
                        {"$set": {f"progress.{data['word']}": {"level": 0, "next_review": 0}}}
                    )
                    st.toast(f"✅ 已添加 {data['word']}，请去复习板块查看！")
            else:
                st.error("抱歉，未找到该单词或 AI 暂时繁忙。")

    elif menu == "🧠 沉浸复习":
        user_doc = db.users.find_one({"_id": username})
        progress = user_doc.get("progress", {})
        
        now = time.time()
        due_words = [w for w, info in progress.items() if info['next_review'] < now]
        
        if not due_words:
            st.balloons()
            st.success("🎉 太棒了！今日复习任务已清空！")
            st.info("快去【极速查词】添加几个新词吧！")
        else:
            if 'current_review_word' not in st.session_state or st.session_state['current_review_word'] not in due_words:
                st.session_state['current_review_word'] = random.choice(due_words)
                st.session_state['show_answer'] = False
            
            w_str = st.session_state['current_review_word']
            word_data = db.library.find_one({"word": w_str})
            
            st.markdown(f"<div style='text-align:center; margin-top:50px;'><h1 style='font-size:3.5rem;'>{w_str}</h1></div>", unsafe_allow_html=True)
            
            if st.button("🔊", key="review_audio"): play_audio(w_str)
            st.markdown("<br>", unsafe_allow_html=True)

            if not st.session_state['show_answer']:
                if st.button("👁️ 查看答案", type="primary", use_container_width=True):
                    st.session_state['show_answer'] = True
                    st.rerun()
            else:
                if word_data:
                    st.markdown(f"""
                    <div class="meaning-box" style="text-align:center;">
                        <span class="meaning-text">{word_data.get('meaning')}</span>
                    </div>
                    <div class="brain-capsule">
                        <span class="brain-tag">🧠 助记</span>
                        <span class="brain-text">{word_data.get('mnemonic', '暂无')}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("#### 你记得怎么样？")
                    c1, c2, c3 = st.columns(3)
                    current_level = progress[w_str].get('level', 0)
                    
                    with c1:
                        if st.button("🔴 忘了", use_container_width=True):
                            new_level = 0
                            db.users.update_one({"_id": username}, {"$set": {f"progress.{w_str}": {"level": new_level, "next_review": get_next_review_time(new_level)}}})
                            st.session_state['show_answer'] = False
                            del st.session_state['current_review_word']
                            st.rerun()
                    with c2:
                        if st.button("🟡 模糊", use_container_width=True):
                            new_level = max(1, current_level)
                            db.users.update_one({"_id": username}, {"$set": {f"progress.{w_str}": {"level": new_level, "next_review": get_next_review_time(new_level)}}})
                            st.session_state['show_answer'] = False
                            del st.session_state['current_review_word']
                            st.rerun()
                    with c3:
                        if st.button("🟢 简单", use_container_width=True):
                            new_level = current_level + 1
                            db.users.update_one({"_id": username}, {"$set": {f"progress.{w_str}": {"level": new_level, "next_review": get_next_review_time(new_level)}}})
                            st.session_state['show_answer'] = False
                            del st.session_state['current_review_word']
                            st.rerun()

    elif menu == "📊 数据中心":
        st.title("📊 学习统计")
        user_doc = db.users.find_one({"_id": username})
        prog = user_doc.get("progress", {})
        total = len(prog)
        mastered = len([k for k,v in prog.items() if v['level'] > 3])
        c1, c2 = st.columns(2)
        c1.metric("累计生词", total)
        c2.metric("熟练掌握", mastered)

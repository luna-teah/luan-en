import streamlit as st
import pandas as pd
import time
import datetime
import json
import random
import hashlib
import os
import secrets
from gtts import gTTS
from io import BytesIO
import pymongo
from openai import OpenAI

# --- 0. 全局配置 ---
st.set_page_config(page_title="Luna Pro V15.1", page_icon="💎", layout="wide")

# 强制配置文件 (浅色主题)
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#4F46E5"\nbackgroundColor="#F3F4F6"\nsecondaryBackgroundColor="#FFFFFF"\ntextColor="#1F2937"\nfont="sans serif"\n')

# --- 1. 🎨 CSS 暴力纠色 (修复看不清字的问题) ---
def local_css():
    st.markdown("""
    <style>
    /* 🔴 核心修复：暴力强制所有文字颜色为深灰，防止白底白字 */
    html, body, [class*="css"] {
        color: #1F2937 !important;
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif;
    }
    
    /* 修复输入框 Label 看不清的问题 */
    .stTextInput label, .stSelectbox label, .stNumberInput label {
        color: #374151 !important;
        font-weight: 600 !important;
    }
    
    /* 修复侧边栏文字 */
    [data-testid="stSidebar"] * {
        color: #1F2937 !important;
    }
    
    /* 隐藏顶部红线 */
    header { visibility: hidden; }
    .stApp { background-color: #F3F4F6; }
    
    /* === 首页导航卡片 === */
    .nav-card {
        background: white; border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center; border: 1px solid #E5E7EB;
        transition: all 0.2s; cursor: pointer; height: 100%;
    }
    .nav-card:hover { transform: translateY(-4px); border-color: #4F46E5; box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); }
    .nav-emoji { font-size: 3rem; margin-bottom: 12px; display: block; }
    .nav-title { font-size: 1.25rem; font-weight: 800; color: #111827 !important; margin-bottom: 8px; }
    .nav-desc { font-size: 0.9rem; color: #6B7280 !important; }

    /* === 单词学习大卡片 === */
    .study-card {
        background: white; border-radius: 24px; padding: 40px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center; margin: 0 auto; max-width: 700px;
        border: 1px solid #E5E7EB;
    }
    .word-main { 
        font-size: 4rem; font-weight: 900; color: #111827 !important; 
        letter-spacing: -0.025em; line-height: 1; margin-bottom: 10px; 
    }
    .word-pho { 
        font-family: 'Georgia', serif; font-size: 1.5rem; 
        color: #6B7280 !important; font-style: italic; margin-bottom: 24px; 
    }
    
    /* 含义区域 */
    .info-section { text-align: left; margin-top: 30px; background: #F9FAFB; padding: 20px; border-radius: 12px; }
    .info-title { font-size: 0.85rem; font-weight: 700; color: #9CA3AF !important; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .info-content { font-size: 1.3rem; color: #1F2937 !important; font-weight: 600; }
    
    /* 脑洞区域 */
    .brain-section { 
        text-align: left; margin-top: 16px; 
        background: #EEF2FF; 
        padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5;
    }
    .brain-text { color: #4338CA !important; font-size: 1.1rem; font-weight: 500; line-height: 1.5; }

    /* 标签与按钮 */
    .tag { display: inline-block; background: #E5E7EB; color: #374151 !important; padding: 4px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; margin-right: 6px; }
    .tag-cat { background: #DCFCE7; color: #166534 !important; }
    
    /* 修复按钮文字 */
    button p { color: inherit !important; }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. 核心连接 ---
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

# --- 3. 智能逻辑 ---
def smart_fetch_word(word_input):
    db = get_db()
    if db is None: return None
    
    query = word_input.strip().lower()
    cached = db.library.find_one({"word": query})
    if cached: return cached
    
    if ai_client:
        try:
            prompt = f"""
            生成单词 "{query}" 的JSON数据:
            {{
                "word": "单词原形", "phonetic": "音标", "meaning": "中文含义(商务优先)",
                "category": "分类(如:商务/生活/物流)", "mnemonic": "中文谐音梗/脑洞记忆",
                "sentences": [{{"en": "英文句", "cn": "中文翻译"}}] (5句)
            }}
            """
            resp = ai_client.chat.completions.create(
                model="deepseek-chat", messages=[{"role":"user","content":prompt}], 
                temperature=1.1, response_format={"type":"json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].lower()
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except: return None
    return None

def smart_batch_generate(topic):
    if ai_client:
        try:
            prompt = f"生成10个关于'{topic}'的核心英文单词(数组格式)，只返回JSON数组 ['word1',...]"
            resp = ai_client.chat.completions.create(
                model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}
            )
            content = resp.choices[0].message.content
            data = json.loads(content)
            if isinstance(data, dict): return list(data.values())[0]
            return data if isinstance(data, list) else []
        except: return []
    return []

# --- 4. 辅助函数 ---
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

# --- 5. 登录 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'user': '', 'menu': 'Home'})

if not st.session_state['logged_in']:
    try:
        token = st.query_params.get("token")
        if token and get_db() is not None:
            u = get_db().users.find_one({"session_token": token})
            if u: st.session_state.update({'logged_in': True, 'user': u['_id']})
    except: pass

def login_page():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br><h1 style='text-align:center; color:#4F46E5;'>💎 Luna Pro</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["登录", "注册"])
        db = get_db()
        with tab1:
            u = st.text_input("用户名", key="l1")
            p = st.text_input("密码", type="password", key="l2")
            if st.button("🚀 登录", use_container_width=True):
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and check_hashes(p, user['password']):
                        token = secrets.token_hex(16)
                        db.users.update_one({"_id": u}, {"$set": {"session_token": token}})
                        st.query_params["token"] = token
                        st.session_state.update({'logged_in': True, 'user': u})
                        st.rerun()
                    else: st.error("密码错误")
                else: st.error("数据库连接失败")
        with tab2:
            nu = st.text_input("新用户名", key="r1")
            np = st.text_input("设置密码", type="password", key="r2")
            if st.button("✨ 注册", use_container_width=True):
                if db and nu and np:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": make_hashes(np), "progress": {}})
                        st.success("注册成功！")
                    else: st.warning("用户已存在")

# --- 6. 主程序 ---
if not st.session_state['logged_in']:
    login_page()
else:
    user = st.session_state['user']
    db = get_db()
    
    # 顶部导航
    c1, c2 = st.columns([8, 2])
    with c1: st.markdown(f"### 👋 Hi, {user}")
    with c2: 
        if st.button("退出登录"):
            if db: db.users.update_one({"_id": user}, {"$set": {"session_token": ""}})
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
    st.divider()

    # 路由
    if st.session_state['menu'] == 'Home':
        st.markdown(f"<h2 style='text-align:center;'>今天想做什么？</h2><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='nav-card'><span class='nav-emoji'>⚡</span><div class='nav-title'>学习新词</div><p class='nav-desc'>按分类 · 排除已学</p></div>", unsafe_allow_html=True)
            if st.button("Go Learn", use_container_width=True): st.session_state['menu']='Learn'; st.rerun()
        with c2:
            st.markdown("<div class='nav-card'><span class='nav-emoji'>🧠</span><div class='nav-title'>智能复习</div><p class='nav-desc'>巩固记忆</p></div>", unsafe_allow_html=True)
            if st.button("Go Review", use_container_width=True): st.session_state['menu']='Review'; st.rerun()
        with c3:
            st.markdown("<div class='nav-card'><span class='nav-emoji'>🚀</span><div class='nav-title'>扩充词库</div><p class='nav-desc'>AI 场景批量生成</p></div>", unsafe_allow_html=True)
            if st.button("Go Add", use_container_width=True): st.session_state['menu']='Add'; st.rerun()

    # --- ⚡ 学习模式 (核心优化) ---
    elif st.session_state['menu'] == 'Learn':
        if st.button("⬅️ 返回大厅"): st.session_state['menu']='Home'; st.rerun()
        st.title("⚡ 学习新词")
        
        # 1. 拿数据
        all_docs = list(db.library.find({}))
        u_prog = db.users.find_one({"_id": user}).get('progress', {})
        
        # 2. 智能分类统计
        # 格式: {"商务": [doc1, doc2], "生活": [doc3]}
        cat_map = {}
        for doc in all_docs:
            if doc['word'] not in u_prog: # 只统计没学过的
                c = doc.get('category', '其他')
                if c not in cat_map: cat_map[c] = []
                cat_map[c].append(doc)
        
        # 3. 生成带数量的选项列表
        # 例如: ["全部 (50)", "商务 (10)", "生活 (5)"]
        total_left = sum([len(v) for v in cat_map.values()])
        options = [f"全部 (剩{total_left}词)"]
        
        # 建立映射方便查找
        selection_key_map = {"全部": "all"}
        
        for cat, docs in cat_map.items():
            label = f"{cat} (剩{len(docs)}词)"
            options.append(label)
            selection_key_map[label] = cat
            
        # 4. 界面选择
        sel_label = st.selectbox("📂 选择你要学习的类别:", options)
        sel_cat = selection_key_map.get(sel_label, "all") # 获取真实分类名
        
        # 5. 过滤出当前要学的词
        current_pool = []
        if sel_cat == "all": # 全部
            for docs in cat_map.values(): current_pool.extend(docs)
        else: # 特定分类
            current_pool = cat_map.get(sel_cat, [])
            
        # 6. 显示卡片
        if not current_pool:
            st.success("🎉 太棒了！这个分类下的单词你都学会了！")
            st.info("💡 提示：去 [扩充词库] 用 AI 生成更多单词吧！")
        else:
            w_data = current_pool[0] # 取第一个
            
            st.markdown(f"""
            <div class="study-card">
                <div class="word-main">{w_data['word']}</div>
                <div class="word-pho">/{w_data.get('phonetic','...')}/</div>
                <div><span class="tag tag-cat">{w_data.get('category','General')}</span></div>
                
                <div class="info-section">
                    <div class="info-title">MEANING</div>
                    <div class="info-content">{w_data.get('meaning')}</div>
                </div>
                
                {'<div class="brain-section"><div class="brain-text">🧠 ' + w_data['mnemonic'] + '</div></div>' if w_data.get('mnemonic') else ''}
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1,2,1])
            with c2:
                st.write("")
                if st.button("🔊 播放发音", use_container_width=True): play_audio(w_data['word'])
                st.markdown("---")
                if st.button("✅ 学会了", type="primary", use_container_width=True):
                    db.users.update_one({"_id": user}, {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": get_next_time(1)}}})
                    st.rerun()

    # --- 🚀 扩充词库 ---
    elif st.session_state['menu'] == 'Add':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        st.title("🚀 智能扩词")
        
        t1, t2 = st.tabs(["查单词", "批量生成"])
        with t1:
            nw = st.text_input("输入单词", key="search")
            if nw:
                with st.spinner("AI thinking..."):
                    d = smart_fetch_word(nw)
                if d: st.success(f"✅ {d['word']} 已入库！"); st.json(d, expanded=False)
        
        with t2:
            st.info("💡 输入场景，AI 自动生成该场景下最常用的 10 个词。")
            topic = st.text_input("输入场景 (如: 商务谈判 / 机场 / 餐厅)", key="topic")
            if st.button("✨ 开始生成", type="primary"):
                if not topic: st.warning("请输入场景")
                else:
                    with st.status("🤖 AI 正在头脑风暴...") as status:
                        lst = smart_batch_generate(topic)
                        status.write(f"找到: {lst}")
                        for w in lst:
                            smart_fetch_word(w)
                        status.update(label="完成！", state="complete")
                    st.success(f"🎉 已添加 {len(lst)} 个词！")

    # --- 🧠 复习模式 ---
    elif st.session_state['menu'] == 'Review':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        st.title("🧠 智能复习")
        
        u_doc = db.users.find_one({"_id": user})
        prog = u_doc.get("progress", {})
        due = [w for w, i in prog.items() if i['next_review'] < time.time()]
        
        if not due:
            st.balloons(); st.info("🎉 今日复习完成！")
        else:
            if 'rw' not in st.session_state or st.session_state['rw'] not in due:
                st.session_state['rw'] = random.choice(due)
                st.session_state['show'] = False
            
            w = st.session_state['rw']
            d = db.library.find_one({"word": w}) or {}
            
            st.markdown(f"<div style='text-align:center;margin:40px;'><h1 style='font-size:4rem;color:#111827 !important;'>{w}</h1></div>", unsafe_allow_html=True)
            
            if not st.session_state['show']:
                if st.button("👁️ 查看答案", type="primary", use_container_width=True):
                    st.session_state['show'] = True; st.rerun()
            else:
                st.markdown(f"<div style='text-align:center;font-size:1.5rem;color:#4F46E5 !important;'>{d.get('meaning','')}</div>", unsafe_allow_html=True)
                if d.get('mnemonic'):
                    st.info(f"🧠 {d['mnemonic']}")
                
                c1, c2, c3 = st.columns(3)
                lvl = prog[w]['level']
                with c1:
                    if st.button("🔴 忘了"):
                        db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": 0, "next_review": get_next_time(0)}}})
                        st.session_state['show']=False; del st.session_state['rw']; st.rerun()
                with c2:
                    if st.button("🟢 记得"):
                        db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": lvl+1, "next_review": get_next_time(lvl+1)}}})
                        st.session_state['show']=False; del st.session_state['rw']; st.rerun()
                with c3:
                    if st.button("🚀 太简单"):
                        db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": lvl+2, "next_review": get_next_time(lvl+2)}}})
                        st.session_state['show']=False; del st.session_state['rw']; st.rerun()

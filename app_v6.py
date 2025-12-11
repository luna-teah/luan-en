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
st.set_page_config(page_title="Luna Pro V15.2", page_icon="💎", layout="wide")

# 强制配置文件
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#4F46E5"\nbackgroundColor="#F3F4F6"\nsecondaryBackgroundColor="#FFFFFF"\ntextColor="#1F2937"\nfont="sans serif"\n')

# --- 1. CSS 美化 (修复乱码问题) ---
def local_css():
    st.markdown("""
    <style>
    /* 基础重置 */
    header { visibility: hidden; }
    .stApp { background-color: #F3F4F6; }
    
    /* 导航卡片 */
    .nav-card {
        background: white; border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; cursor: pointer; transition: all 0.2s;
    }
    .nav-card:hover { transform: translateY(-5px); border-color: #4F46E5; box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    
    /* 单词学习卡 - 核心修复区域 */
    .study-card {
        background: white; border-radius: 20px; padding: 40px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center; margin: 0 auto; max-width: 700px;
        border: 1px solid #E5E7EB;
    }
    .word-title { font-size: 3.5rem; font-weight: 800; color: #111827; margin: 0; line-height: 1.2; }
    .word-pho { font-family: 'Georgia', serif; font-size: 1.4rem; color: #6B7280; font-style: italic; margin-bottom: 20px; }
    
    /* 信息块 */
    .info-box { text-align: left; background: #F9FAFB; padding: 20px; border-radius: 12px; margin-top: 20px; border: 1px solid #E5E7EB; }
    .info-label { font-size: 0.8rem; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 5px; }
    .info-text { font-size: 1.2rem; color: #374151; font-weight: 600; }
    
    /* 脑洞块 */
    .brain-box { 
        text-align: left; margin-top: 15px; 
        background: linear-gradient(to right, #EEF2FF, #ffffff);
        padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5;
    }
    .brain-text { color: #4338CA; font-size: 1.1rem; font-weight: 500; }
    
    /* 标签 */
    .tag { display: inline-block; background: #E5E7EB; color: #374151; padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; font-weight: 600; margin: 5px; }
    .tag-cat { background: #DCFCE7; color: #166534; }
    </style>
    """, unsafe_allow_html=True)
local_css()

# --- 2. 连接服务 ---
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

# --- 3. 辅助函数 ---
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

# --- 4. 核心：智能查词 (修复AI逻辑) ---
def smart_fetch(word):
    db = get_db()
    if db is None: 
        st.error("数据库未连接 (请检查MongoDB IP白名单)")
        return None
    
    # 1. 查缓存
    cached = db.library.find_one({"word": word.lower().strip()})
    if cached: return cached
    
    # 2. AI 生成
    if ai_client:
        try:
            prompt = f"""
            生成单词 "{word}" 的JSON数据:
            {{
                "word": "单词", "phonetic": "音标", "meaning": "中文含义(商务优先)",
                "category": "分类(如:商务/生活/物流)", "mnemonic": "中文谐音梗/脑洞记忆",
                "sentences": [{{"en": "英文句", "cn": "中文翻译"}}] (5句)
            }}
            """
            resp = ai_client.chat.completions.create(
                model="deepseek-chat", messages=[{"role":"user","content":prompt}], 
                temperature=1.1, response_format={"type":"json_object"}
            )
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].lower().strip()
            # 存入数据库
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            if "402" in str(e):
                st.error("⚠️ AI 余额不足。请给 DeepSeek 充值。")
            else:
                st.error(f"AI Error: {e}")
            return None
    return None

def batch_gen(topic):
    if not ai_client: return []
    try:
        prompt = f"列出10个关于'{topic}'的核心英文单词(数组格式)，只返回JSON数组。"
        resp = ai_client.chat.completions.create(
            model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"}
        )
        content = resp.choices[0].message.content
        data = json.loads(content)
        if isinstance(data, dict): return list(data.values())[0] 
        return data if isinstance(data, list) else []
    except: return []

# --- 5. 登录系统 ---
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
    st.markdown("<br><h1 style='text-align:center;color:#4F46E5'>💎 Luna Pro V15.2</h1>", unsafe_allow_html=True)
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
            else: st.error("❌ 无法连接数据库，请检查 MongoDB IP 白名单 (0.0.0.0/0)")
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
    
    # 顶部
    c1, c2 = st.columns([8, 2])
    with c1: st.markdown(f"### 👋 Hi, {user}")
    with c2: 
        if st.button("退出"):
            if db: db.users.update_one({"_id": user}, {"$set": {"session_token": ""}})
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()
    st.divider()

    if st.session_state['menu'] == 'Home':
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='nav-card'><h3>⚡ 学习新词</h3><p>按分类学习 · 排除已学</p></div>", unsafe_allow_html=True)
            if st.button("Go Learn", use_container_width=True): st.session_state['menu']='Learn'; st.rerun()
        with c2:
            st.markdown("<div class='nav-card'><h3>🧠 智能复习</h3><p>艾宾浩斯算法</p></div>", unsafe_allow_html=True)
            if st.button("Go Review", use_container_width=True): st.session_state['menu']='Review'; st.rerun()
        with c3:
            st.markdown("<div class='nav-card'><h3>🚀 扩充词库</h3><p>AI 批量生成场景词</p></div>", unsafe_allow_html=True)
            if st.button("Go Add", use_container_width=True): st.session_state['menu']='Add'; st.rerun()

    # --- 学习模式 (修复乱码) ---
    elif st.session_state['menu'] == 'Learn':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        st.title("⚡ 学习新词")
        
        all_words = list(db.library.find({}))
        cats = list(set([w.get('category','未分类') for w in all_words]))
        
        # 统计数量
        u_prog = db.users.find_one({"_id": user}).get('progress', {})
        cat_counts = {}
        for c in cats:
            count = len([w for w in all_words if w.get('category') == c and w['word'] not in u_prog])
            cat_counts[c] = count
            
        options = [f"{c} (剩{n}词)" for c, n in cat_counts.items() if n > 0]
        options.insert(0, "全部")
        
        sel_opt = st.selectbox("选择分类", options)
        
        pool = []
        for w in all_words:
            if w['word'] not in u_prog:
                if sel_opt == "全部": pool.append(w)
                elif w.get('category') in sel_opt: pool.append(w)
        
        if not pool:
            st.success("🎉 该分类已学完！去扩充词库吧。")
        else:
            w_data = pool[0]
            
            # --- 修复后的卡片渲染 ---
            # 1. 脑洞部分 (独立处理，防止乱码)
            brain_html = ""
            if w_data.get('mnemonic'):
                brain_html = f"""
                <div class="brain-box">
                    <div class="info-label">🧠 脑洞记忆</div>
                    <div class="brain-text">{w_data['mnemonic']}</div>
                </div>
                """
            
            # 2. 主卡片 HTML
            st.markdown(f"""
            <div class="study-card">
                <div class="word-title">{w_data['word']}</div>
                <div class="word-pho">/{w_data.get('phonetic','...')}/</div>
                <div><span class="tag tag-cat">{w_data.get('category','General')}</span></div>
                
                <div class="info-box">
                    <div class="info-label">MEANING</div>
                    <div class="info-text">{w_data.get('meaning')}</div>
                </div>
                
                {brain_html}
            </div>
            """, unsafe_allow_html=True)
            
            # 3. 按钮区
            c1, c2, c3 = st.columns([1,2,1])
            with c2:
                st.write("")
                if st.button("🔊 播放发音", use_container_width=True): play_audio(w_data['word'])
                st.markdown("---")
                if st.button("✅ 我学会了", type="primary", use_container_width=True):
                    db.users.update_one({"_id": user}, {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": get_next_time(1)}}})
                    st.rerun()
            
            # 4. 例句区 (独立渲染，防止 HTML 嵌套错误)
            st.markdown("### 📚 场景例句")
            for sent in w_data.get('sentences', []):
                st.markdown(f"**{sent.get('en')}**")
                st.caption(f"{sent.get('cn')}")
                st.divider()

    # --- 扩充词库 ---
    elif st.session_state['menu'] == 'Add':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        st.title("🚀 智能扩词")
        
        t1, t2 = st.tabs(["查单词", "批量生成"])
        with t1:
            nw = st.text_input("输入单词回车", key="search")
            if nw:
                with st.spinner("AI thinking..."):
                    d = smart_fetch(nw)
                if d: st.success(f"✅ {d['word']} 已入库！"); st.json(d, expanded=False)
        
        with t2:
            st.info("💡 输入场景，AI 自动生成 10 个词。")
            topic = st.text_input("输入场景 (如: 机场)", key="topic")
            if st.button("✨ 生成", type="primary"):
                if not topic: st.warning("请输入场景")
                else:
                    with st.status("AI 正在生成...") as status:
                        lst = batch_gen(topic)
                        status.write(f"找到: {lst}")
                        for w in lst:
                            smart_fetch(w)
                        status.update(label="完成！", state="complete")
                    st.success(f"🎉 已添加 {len(lst)} 个词！")

    # --- 复习模式 ---
    elif st.session_state['menu'] == 'Review':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        
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
            
            st.markdown(f"<div style='text-align:center;margin:40px;'><h1 style='font-size:4rem;'>{w}</h1></div>", unsafe_allow_html=True)
            if not st.session_state['show']:
                if st.button("👁️ 查看答案", type="primary", use_container_width=True):
                    st.session_state['show'] = True; st.rerun()
            else:
                st.info(f"{d.get('meaning')} \n\n 🧠 {d.get('mnemonic','')}")
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

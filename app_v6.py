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
st.set_page_config(page_title="Luna Pro V17", page_icon="💎", layout="wide")

# 强制配置文件
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#4F46E5"\nbackgroundColor="#F3F4F6"\nsecondaryBackgroundColor="#FFFFFF"\ntextColor="#1F2937"\nfont="sans serif"\n')

# --- 1. CSS 美化 (修复乱码的关键) ---
def local_css():
    st.markdown("""
    <style>
    /* 强制隐藏默认表头 */
    header {visibility: hidden;}
    .stApp { background-color: #F3F4F6; }
    
    /* 修复文字颜色 */
    h1, h2, h3, p, div, span, label { color: #1F2937 !important; font-family: sans-serif; }
    
    /* 导航卡片 */
    .nav-card {
        background: white; border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; cursor: pointer; transition: all 0.2s;
        height: 100%; display: flex; flex-direction: column; justify-content: center;
    }
    .nav-card:hover { transform: translateY(-5px); border-color: #4F46E5; box-shadow: 0 10px 15px rgba(0,0,0,0.1); }
    
    /* 单词学习卡 */
    .word-card {
        background: white; border-radius: 20px; padding: 40px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center; margin: 0 auto; max-width: 800px;
        border: 1px solid #E5E7EB; margin-bottom: 20px;
    }
    
    /* 信息块样式 */
    .info-box { 
        text-align: left; background: #F9FAFB; 
        padding: 20px; border-radius: 12px; margin-top: 20px; 
        border: 1px solid #E5E7EB; 
    }
    
    .brain-box { 
        text-align: left; margin-top: 15px; 
        background: linear-gradient(to right, #EEF2FF, #ffffff);
        padding: 20px; border-radius: 12px; border-left: 5px solid #4F46E5;
    }
    
    /* 标签 */
    .tag-pill { 
        display: inline-block; background: #E5E7EB; color: #374151; 
        padding: 4px 12px; border-radius: 99px; font-size: 0.8rem; 
        font-weight: 600; margin: 5px; 
    }
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

# --- 3. 核心工具 ---
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

def smart_fetch(word):
    db = get_db()
    if db is None: return None
    cached = db.library.find_one({"word": word.lower().strip()})
    if cached: return cached
    
    if ai_client:
        try:
            prompt = f"""
            生成单词 "{word}" 的JSON数据:
            {{
                "word": "单词", "phonetic": "音标", "meaning": "含义(商务优先)",
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
            data['created_at'] = datetime.datetime.now()
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            # 优雅处理欠费
            if "402" in str(e): st.error("⚠️ DeepSeek 余额不足，无法生成。")
            else: st.error(f"AI Error: {e}")
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

# --- 4. 登录逻辑 ---
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
    st.markdown("<br><br><h1 style='text-align:center;color:#4F46E5'>💎 Luna Pro V17</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
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
                else: st.error("无法连接数据库 (请检查IP白名单)")
        with tab2:
            nu = st.text_input("新用户名", key="r1")
            np = st.text_input("设置密码", type="password", key="r2")
            if st.button("✨ 注册", use_container_width=True):
                if db and nu and np:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": make_hashes(np), "progress": {}})
                        st.success("注册成功！")
                    else: st.warning("用户已存在")

# --- 5. 主程序 (单文件架构) ---
if not st.session_state['logged_in']:
    login_page()
else:
    user = st.session_state['user']
    db = get_db()
    
    # 侧边栏导航
    with st.sidebar:
        st.title(f"Hi, {user}")
        nav = st.radio("导航菜单", ["🏠 主页大厅", "⚡ 学习新词", "🧠 智能复习", "🚀 扩充词库", "📊 数据中心"])
        
        # 映射导航
        if nav == "🏠 主页大厅": st.session_state['menu'] = 'Home'
        elif nav == "⚡ 学习新词": st.session_state['menu'] = 'Learn'
        elif nav == "🧠 智能复习": st.session_state['menu'] = 'Review'
        elif nav == "🚀 扩充词库": st.session_state['menu'] = 'Add'
        elif nav == "📊 数据中心": st.session_state['menu'] = 'Stats'
        
        st.divider()
        if st.button("退出登录"):
            if db: db.users.update_one({"_id": user}, {"$set": {"session_token": ""}})
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    # --- 页面路由 ---
    
    # 🏠 主页
    if st.session_state['menu'] == 'Home':
        st.markdown(f"<h2 style='text-align:center;'>👋 欢迎回来!</h2><br>", unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("<div class='nav-card'><span style='font-size:3rem'>⚡</span><h3>学习新词</h3><p>按分类学习</p></div>", unsafe_allow_html=True)
            if st.button("Go Learn", use_container_width=True): st.session_state['menu']='Learn'; st.rerun()
        with c2:
            st.markdown("<div class='nav-card'><span style='font-size:3rem'>🧠</span><h3>智能复习</h3><p>巩固记忆</p></div>", unsafe_allow_html=True)
            if st.button("Go Review", use_container_width=True): st.session_state['menu']='Review'; st.rerun()
        with c3:
            st.markdown("<div class='nav-card'><span style='font-size:3rem'>🚀</span><h3>扩充词库</h3><p>AI 自动生成</p></div>", unsafe_allow_html=True)
            if st.button("Go Add", use_container_width=True): st.session_state['menu']='Add'; st.rerun()

    # ⚡ 学习模式
    elif st.session_state['menu'] == 'Learn':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        st.title("⚡ 学习新词")
        
        all_words = list(db.library.find({}))
        cats = list(set([w.get('category','未分类') for w in all_words]))
        
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
                target_c = sel_opt.split(" (")[0]
                if sel_opt == "全部": pool.append(w)
                elif w.get('category') == target_c: pool.append(w)
        
        if not pool:
            st.success("🎉 该分类已学完！")
        else:
            w_data = pool[0]
            # 渲染卡片 (这里修复了乱码)
            st.markdown(f"""
            <div class="word-card">
                <h1 style="color:#4F46E5; font-size:3.5rem; margin:0;">{w_data['word']}</h1>
                <p style="color:#666; font-size:1.2rem; font-style:italic;">/{w_data.get('phonetic','...')}/</p>
                <span class="tag-pill">{w_data.get('category','General')}</span>
                
                <div class="info-box">
                    <div style="font-size:0.8rem; font-weight:bold; color:#999;">MEANING</div>
                    <div style="font-size:1.3rem; font-weight:bold; color:#333;">{w_data.get('meaning')}</div>
                </div>
                
                {'<div class="brain-box"><div style="color:#4F46E5; font-weight:bold;">🧠 脑洞记忆</div><div style="font-size:1.1rem;">'+w_data['mnemonic']+'</div></div>' if w_data.get('mnemonic') else ''}
            </div>
            """, unsafe_allow_html=True)
            
            c1, c2, c3 = st.columns([1,2,1])
            with c2:
                if st.button("🔊 播放发音", use_container_width=True): play_audio(w_data['word'])
                st.markdown("---")
                if st.button("✅ 我学会了", type="primary", use_container_width=True):
                    db.users.update_one({"_id": user}, {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": get_next_time(1)}}})
                    st.rerun()
            
            # 例句
            st.markdown("### 📚 场景例句")
            for sent in w_data.get('sentences', []):
                st.markdown(f"**{sent.get('en')}**")
                st.caption(f"{sent.get('cn')}")
                st.divider()

    # 🚀 扩充词库
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

    # 🧠 复习模式
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
            
            st.markdown(f"""
            <div class="word-card">
                <h1 style="color:#1F2937; font-size:4rem;">{w}</h1>
            </div>
            """, unsafe_allow_html=True)
            
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

    # 📊 数据中心
    elif st.session_state['menu'] == 'Stats':
        if st.button("⬅️ 返回"): st.session_state['menu']='Home'; st.rerun()
        st.title("📊 学习数据")
        u_doc = db.users.find_one({"_id": user})
        prog = u_doc.get("progress", {})
        c1, c2 = st.columns(2)
        c1.metric("累计学习单词", len(prog))
        c2.metric("熟练掌握 (>L3)", len([k for k,v in prog.items() if v['level']>3]))

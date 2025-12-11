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
st.set_page_config(page_title="Luna Pro V15", page_icon="💎", layout="wide") # 宽屏布局更像桌面软件

# 强制配置文件
if not os.path.exists(".streamlit"):
    os.makedirs(".streamlit")
with open(".streamlit/config.toml", "w") as f:
    f.write('[theme]\nbase="light"\nprimaryColor="#4F46E5"\nbackgroundColor="#F3F4F6"\nsecondaryBackgroundColor="#FFFFFF"\ntextColor="#1F2937"\nfont="sans serif"\n')

# --- 1. 🎨 CSS 颜值革命 (Notion/现代风) ---
def local_css():
    st.markdown("""
    <style>
    /* 全局优化 */
    .stApp { background-color: #F3F4F6; }
    header { visibility: hidden; }
    
    /* 首页大卡片 */
    .nav-card {
        background: white; border-radius: 16px; padding: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        text-align: center; border: 1px solid #E5E7EB;
        transition: all 0.2s; cursor: pointer; height: 100%;
    }
    .nav-card:hover { transform: translateY(-4px); box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.1); border-color: #4F46E5; }
    .nav-emoji { font-size: 3rem; margin-bottom: 12px; display: block; }
    .nav-title { font-size: 1.25rem; font-weight: 700; color: #111827; margin-bottom: 8px; }
    .nav-desc { font-size: 0.9rem; color: #6B7280; }

    /* 单词学习卡 */
    .study-card {
        background: white; border-radius: 24px; padding: 40px;
        box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        text-align: center; margin: 0 auto; max-width: 700px;
        border: 1px solid #E5E7EB;
    }
    .word-main { font-size: 4rem; font-weight: 800; color: #111827; letter-spacing: -0.025em; line-height: 1; margin-bottom: 10px; }
    .word-pho { font-family: 'Georgia', serif; font-size: 1.5rem; color: #6B7280; font-style: italic; margin-bottom: 24px; }
    
    /* 含义与脑洞 */
    .info-section { text-align: left; margin-top: 30px; background: #F9FAFB; padding: 20px; border-radius: 12px; }
    .info-title { font-size: 0.85rem; font-weight: 700; color: #9CA3AF; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 8px; }
    .info-content { font-size: 1.2rem; color: #374151; font-weight: 500; }
    
    .brain-section { 
        text-align: left; margin-top: 16px; 
        background: linear-gradient(135deg, #EEF2FF 0%, #E0E7FF 100%); 
        padding: 20px; border-radius: 12px; border-left: 4px solid #4F46E5;
    }
    .brain-text { color: #4338CA; font-size: 1.1rem; font-weight: 500; }

    /* 标签药丸 */
    .tag { display: inline-block; background: #E5E7EB; color: #374151; padding: 4px 12px; border-radius: 999px; font-size: 0.8rem; font-weight: 600; margin-right: 6px; margin-bottom: 6px; }
    .tag-cat { background: #DCFCE7; color: #166534; }
    
    /* 统计条 */
    .stat-bar { height: 8px; background: #E5E7EB; border-radius: 4px; overflow: hidden; margin-top: 8px; }
    .stat-fill { height: 100%; background: #4F46E5; }
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

# --- 3. 智能逻辑 (含场景生成) ---
def smart_fetch_word(word_input, mode="word"):
    db = get_db()
    if db is None: return None
    
    # 清洗输入
    query = word_input.strip()
    
    # 模式A: 单个单词查询 (Word Mode)
    # 先查库
    cached = db.library.find_one({"word": query.lower()})
    if cached: return cached
    
    # AI 生成
    if ai_client:
        prompt = f"""
        请生成单词 "{query}" 的 JSON 数据。
        Schema: {{
            "word": "英文单词",
            "phonetic": "音标",
            "meaning": "中文含义(商务/外贸优先)",
            "category": "所属分类(例如: 商务/生活/物流/合同)",
            "mnemonic": "好记的中文脑洞/谐音梗",
            "sentences": [{{"en": "英文句", "cn": "中文翻译"}}, ...5句]
        }}
        仅返回JSON。
        """
        try:
            resp = ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                temperature=1.1,
                response_format={ "type": "json_object" }
            )
            data = json.loads(resp.choices[0].message.content)
            data['word'] = data['word'].lower()
            # 存入数据库
            db.library.update_one({"word": data['word']}, {"$set": data}, upsert=True)
            return data
        except Exception as e:
            st.error(f"AI Error: {e}")
            return None
    return None

def smart_batch_generate(topic):
    # 模式B: 场景批量生成 (Topic Mode)
    if ai_client:
        prompt = f"""
        我是一个外贸业务员。请围绕主题 "{topic}"，推荐 10 个最核心的英文单词。
        返回一个纯 JSON 字符串数组，例如: ["word1", "word2", ...]
        不要返回任何其他解释。
        """
        try:
            resp = ai_client.chat.completions.create(
                model="deepseek-chat",
                messages=[{"role": "user", "content": prompt}],
                response_format={ "type": "json_object" } # DeepSeek有时候需要明确指示
            )
            # 处理可能的格式差异，这里尝试解析列表
            content = resp.choices[0].message.content
            # 兼容处理：如果返回的是 { "words": [...] }
            try:
                data = json.loads(content)
                if isinstance(data, list): words = data
                elif isinstance(data, dict): words = list(data.values())[0]
                else: words = []
            except: return []
            
            return [w.lower() for w in words if isinstance(w, str)]
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

# --- 5. 登录/自动登录 ---
if 'logged_in' not in st.session_state:
    st.session_state.update({'logged_in': False, 'username': '', 'menu': 'Home'})

# 自动登录
if not st.session_state['logged_in']:
    try:
        token = st.query_params.get("token")
        if token and get_db() is not None:
            user = get_db().users.find_one({"session_token": token})
            if user:
                st.session_state.update({'logged_in': True, 'username': user['_id']})
    except: pass

def login_page():
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<br><h1 style='text-align:center;'>💎 Luna Pro V15</h1>", unsafe_allow_html=True)
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        db = get_db()
        with tab1:
            u = st.text_input("Username", key="l_u")
            p = st.text_input("Password", type="password", key="l_p")
            if st.button("🚀 Login", use_container_width=True):
                if db is not None:
                    user = db.users.find_one({"_id": u})
                    if user and check_hashes(p, user['password']):
                        token = secrets.token_hex(16)
                        db.users.update_one({"_id": u}, {"$set": {"session_token": token}})
                        st.query_params["token"] = token
                        st.session_state.update({'logged_in': True, 'username': u})
                        st.rerun()
                    else: st.error("Invalid credentials")
                else: st.error("DB Error")
        with tab2:
            nu = st.text_input("New Username", key="r_u")
            np = st.text_input("New Password", type="password", key="r_p")
            if st.button("✨ Create Account", use_container_width=True):
                if db is not None and nu and np:
                    if not db.users.find_one({"_id": nu}):
                        db.users.insert_one({"_id": nu, "password": make_hashes(np), "progress": {}, "stats": {"streak": 0}})
                        st.success("Success! Please login.")
                    else: st.warning("Username taken")

# --- 6. 主程序 ---
if not st.session_state['logged_in']:
    login_page()
else:
    user = st.session_state['username']
    db = get_db()
    
    # 顶部导航栏
    c_logo, c_nav, c_user = st.columns([2, 6, 2])
    with c_logo:
        st.markdown(f"### 💎 Luna Pro")
    with c_user:
        if st.button("🚪 退出"):
            if db: db.users.update_one({"_id": user}, {"$set": {"session_token": ""}})
            st.query_params.clear()
            st.session_state.clear()
            st.rerun()

    st.divider()

    # 路由控制
    if 'menu' not in st.session_state: st.session_state['menu'] = 'Home'
    
    # --- 🏠 首页大厅 ---
    if st.session_state['menu'] == 'Home':
        st.markdown(f"<h2 style='text-align:center;'>👋 Hi, {user}! 今天想做什么？</h2><br>", unsafe_allow_html=True)
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown("""
            <div class="nav-card">
                <span class="nav-emoji">⚡</span>
                <div class="nav-title">学习新词</div>
                <div class="nav-desc">按分类学习 · 自动排除已学</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Go Learn", key="btn_learn", use_container_width=True):
                st.session_state['menu'] = 'Learn'
                st.rerun()
                
        with c2:
            st.markdown("""
            <div class="nav-card">
                <span class="nav-emoji">🧠</span>
                <div class="nav-title">智能复习</div>
                <div class="nav-desc">艾宾浩斯算法 · 巩固记忆</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Go Review", key="btn_review", use_container_width=True):
                st.session_state['menu'] = 'Review'
                st.rerun()
                
        with c3:
            st.markdown("""
            <div class="nav-card">
                <span class="nav-emoji">🚀</span>
                <div class="nav-title">扩充词库</div>
                <div class="nav-desc">输入场景/单词 · AI 批量生成</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Go Add", key="btn_add", use_container_width=True):
                st.session_state['menu'] = 'Add'
                st.rerun()

    # --- ⚡ 学习模式 (分类筛选) ---
    elif st.session_state['menu'] == 'Learn':
        col_back, col_title = st.columns([1, 8])
        with col_back:
            if st.button("⬅️ 返回"):
                st.session_state['menu'] = 'Home'
                st.rerun()
        with col_title: st.title("⚡ 学习新词")

        # 1. 获取所有词和分类
        all_words = list(db.library.find({}))
        # 统计分类
        categories = list(set([w.get('category', '未分类') for w in all_words]))
        if '未分类' not in categories: categories.append('未分类')
        
        # 2. 选择分类
        selected_cat = st.selectbox("📂 选择单词分类", ["全部"] + categories)
        
        # 3. 过滤逻辑：该分类下 & 未学过(not in progress)
        user_progress = db.users.find_one({"_id": user}).get('progress', {})
        
        pool = []
        for w in all_words:
            w_cat = w.get('category', '未分类')
            if selected_cat == "全部" or selected_cat == w_cat:
                if w['word'] not in user_progress: # 只要没学过
                    pool.append(w)
        
        st.caption(f"当前分类剩余: {len(pool)} 个生词")
        st.progress(0 if len(all_words)==0 else (len(all_words)-len(pool))/len(all_words))
        
        if not pool:
            st.success("🎉 该分类下的单词已全部学完！去选别的类吧。")
        else:
            # 每次取第一个
            w_data = pool[0]
            
            # --- 渲染卡片 ---
            st.markdown(f"""
            <div class="study-card">
                <div class="word-main">{w_data['word']}</div>
                <div class="word-pho">/{w_data.get('phonetic', '...')}/</div>
                <div>
                    <span class="tag tag-cat">{w_data.get('category', 'General')}</span>
                </div>
                
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
                if st.button("🔊 播放发音", use_container_width=True):
                    play_audio(w_data['word'])
                
                st.markdown("---")
                if st.button("✅ 我学会了", type="primary", use_container_width=True):
                    # 存入进度 level 1
                    db.users.update_one(
                        {"_id": user},
                        {"$set": {f"progress.{w_data['word']}": {"level": 1, "next_review": get_next_time(1)}}}
                    )
                    st.rerun()

    # --- 🚀 扩充词库 (场景生成) ---
    elif st.session_state['menu'] == 'Add':
        col_back, col_title = st.columns([1, 8])
        with col_back:
            if st.button("⬅️ 返回"):
                st.session_state['menu'] = 'Home'
                st.rerun()
        with col_title: st.title("🚀 智能扩词")
        
        tab_word, tab_topic = st.tabs(["查单词", "🔮 按场景批量生成"])
        
        with tab_word:
            new_word = st.text_input("输入单词 (回车自动查)", placeholder="例如: invoice")
            if new_word:
                with st.spinner("AI 正在分析..."):
                    data = smart_fetch_word(new_word)
                if data:
                    st.success(f"✅ [{data['word']}] 已入库！分类: {data.get('category')}")
                    # 显示一下刚才查的
                    st.json(data, expanded=False)
        
        with tab_topic:
            st.info("💡 输入一个场景，AI 会自动为你推荐并生成 10 个相关单词入库。")
            topic = st.text_input("输入场景 (例如: 机场 / 谈判 / 或者是'骂人的话')", placeholder="例如: 国际物流")
            if st.button("✨ 开始生成 (耗时约10秒)", type="primary"):
                if not topic: st.warning("请输入场景")
                else:
                    with st.status("🤖 AI 正在工作中...") as status:
                        status.write(f"正在思考 [{topic}] 相关的核心词汇...")
                        word_list = smart_batch_generate(topic)
                        status.write(f"找到 {len(word_list)} 个词: {', '.join(word_list)}")
                        
                        count = 0
                        for w in word_list:
                            status.write(f"正在生成详情: {w}...")
                            smart_fetch_word(w) # 逐个生成并存库
                            count += 1
                        
                        status.update(label="✅ 全部完成！", state="complete")
                    
                    st.balloons()
                    st.success(f"🎉 成功添加 {count} 个单词到词库！快去【学习模式】查看吧！")

    # --- 🧠 复习模式 (保持 V14 逻辑) ---
    elif st.session_state['menu'] == 'Review':
        col_back, col_title = st.columns([1, 8])
        with col_back:
            if st.button("⬅️ 返回"): st.session_state['menu'] = 'Home'; st.rerun()
        with col_title: st.title("🧠 智能复习")
        
        # ... (复习逻辑与之前相同，节省篇幅，这里复用核心逻辑) ...
        # 获取复习词
        user_doc = db.users.find_one({"_id": user})
        progress = user_doc.get("progress", {})
        now = time.time()
        due = [w for w, info in progress.items() if info['next_review'] < now]
        
        if not due:
            st.balloons()
            st.info("太棒了！所有单词都复习完了。")
        else:
            if 'rev_w' not in st.session_state or st.session_state['rev_w'] not in due:
                st.session_state['rev_w'] = random.choice(due)
                st.session_state['show'] = False
            
            w = st.session_state['rev_w']
            data = db.library.find_one({"word": w}) or {}
            
            st.markdown(f"<div style='text-align:center;margin:40px;'><h1 style='font-size:4rem;'>{w}</h1></div>", unsafe_allow_html=True)
            
            if not st.session_state['show']:
                if st.button("👁️ 查看答案", type="primary", use_container_width=True):
                    st.session_state['show'] = True
                    st.rerun()
            else:
                st.markdown(f"<div style='text-align:center;font-size:1.5rem;color:#4F46E5;'>{data.get('meaning','')}</div>", unsafe_allow_html=True)
                if data.get('mnemonic'):
                    st.info(f"🧠 {data['mnemonic']}")
                
                c1, c2, c3 = st.columns(3)
                curr_lvl = progress[w]['level']
                with c1:
                    if st.button("🔴 忘了"):
                        db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": 0, "next_review": get_next_time(0)}}})
                        st.session_state['show'] = False; del st.session_state['rev_w']; st.rerun()
                with c2:
                    if st.button("🟢 记得"):
                        nl = curr_lvl + 1
                        db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": nl, "next_review": get_next_time(nl)}}})
                        st.session_state['show'] = False; del st.session_state['rev_w']; st.rerun()
                with c3:
                    if st.button("🚀 太简单"):
                        nl = curr_lvl + 2
                        db.users.update_one({"_id": user}, {"$set": {f"progress.{w}": {"level": nl, "next_review": get_next_time(nl)}}})
                        st.session_state['show'] = False; del st.session_state['rev_w']; st.rerun()

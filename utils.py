import streamlit as st
import pymongo
from openai import OpenAI
import hashlib
from gtts import gTTS
from io import BytesIO
import time
import datetime
import json

# --- 1. CSS 核弹级修复 (强制高对比度) ---
def local_css():
    st.markdown("""
    <style>
    /* 1. 强制覆盖 Streamlit 默认主题，锁死背景和文字颜色 */
    [data-testid="stAppViewContainer"] {
        background-color: #F3F4F6 !important; /* 浅灰背景 */
    }
    
    /* 2. 暴力强制所有文字变成深黑色 (#111827) */
    .stApp, .stApp p, .stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5, .stApp h6, 
    .stApp div, .stApp span, .stApp label, .stApp li, .stApp button {
        color: #111827 !important; 
        font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif !important;
    }
    
    /* 3. 修复输入框看不清的问题 (白底黑字) */
    .stTextInput input, .stSelectbox div, .stNumberInput input {
        color: #111827 !important;
        background-color: #FFFFFF !important;
        border-color: #D1D5DB !important;
    }
    
    /* 4. 修复侧边栏文字 */
    [data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 1px solid #E5E7EB !important;
    }
    [data-testid="stSidebar"] * {
        color: #1F2937 !important;
    }

    /* 5. 隐藏顶部红线 */
    header { visibility: hidden; }
    
    /* === 自定义卡片样式 (不受主题影响) === */
    .nav-card {
        background: white !important; 
        padding: 24px; border-radius: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center;
        border: 1px solid #E5E7EB; cursor: pointer; transition: all 0.2s;
        height: 100%;
    }
    .nav-card:hover { transform: translateY(-5px); border-color: #4F46E5; }
    .nav-title { color: #111827 !important; font-weight: 900 !important; font-size: 1.25rem !important; }
    .nav-desc { color: #6B7280 !important; font-size: 0.9rem !important; }
    
    .word-card {
        background: #FFFFFF !important; 
        border-radius: 20px; padding: 40px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.08); 
        text-align: center; border: 1px solid #E5E7EB; 
        margin-bottom: 25px;
    }
    
    .big-word { 
        color: #111827 !important; font-size: 3.5rem !important; font-weight: 900 !important; margin: 0 !important; 
    }
    
    .meaning-box {
        background: #ECFDF5 !important; border-left: 5px solid #10B981 !important;
        padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px;
    }
    .meaning-text { color: #065F46 !important; font-weight: bold !important; font-size: 1.2rem !important; }
    
    .brain-box {
        background: #EEF2FF !important; border-left: 5px solid #6366F1 !important;
        padding: 15px; text-align: left; border-radius: 8px; margin-top: 15px;
    }
    .brain-text { color: #4338CA !important; font-weight: 500 !important; }
    
    .tag-pill {
        background: #E5E7EB !important; color: #374151 !important;
        padding: 4px 12px; border-radius: 99px; font-weight: 600;
    }
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
    try: return OpenAI(api_key=st.secrets["deepseek"]["api_key"], base_url=st.secrets["deepseek"]["base_url

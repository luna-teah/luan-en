import streamlit as st
import utils

st.set_page_config(page_title="扩充词库", layout="wide")
utils.local_css()

# 侧边栏返回
with st.sidebar:
    if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")

st.title("🚀 智能扩词")

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("请先登录")
    st.stop()

db = utils.get_db()

tab1, tab2 = st.tabs(["🔍 查单词", "✨ 批量生成"])

# --- 查单个单词 ---
with tab1:
    w = st.text_input("输入单词 (支持中文自动翻译)")
    if st.button("查询入库"):
        if w:
            with st.spinner("AI 正在分析..."):
                d = utils.smart_fetch(w)
            if d: 
                st.success(f"✅ {d['word']} 已入库！")
                st.json(d) # 简单展示结果

# --- 批量生成 ---
with tab2:
    st.info("💡 AI 会自动避开你词库里已有的单词")
    
    col1, col2 = st.columns([3, 1])
    with col1:
        topic = st.text_input("输入场景 (如: 机场 / 吵架 / 商务邮件)")
    with col2:
        count = st.selectbox("生成数量", [10, 20, 50], index=0)
        
    if st.button("✨ 开始生成", type="primary"):
        if topic:
            # 1. 获取现有词库，用于去重
            existing_words = [x['word'].lower() for x in db.library.find({}, {'word': 1})]
            
            with st.status(f"正在生成 {count} 个相关单词...") as status:
                # 2. 调用 AI 生成 (传入已有单词列表)
                raw_list = utils.batch_gen(topic, count, existing_words)
                
                if not raw_list:
                    status.update(label="生成失败，可能是余额不足或网络波动", state="error")
                else:
                    # 3. 本地二次去重 (双重保险)
                    final_list = [w for w in raw_list if w.lower() not in existing_words]
                    
                    status.write(f"AI 推荐了 {len(raw_list)} 个，去重后剩余 {len(final_list)} 个新词")
                    
                    # 4. 逐个生成详情并入库
                    progress_bar = st.progress(0)
                    for i, word in enumerate(final_list):
                        status.write(f"正在生成详情: {word}...")
                        utils.smart_fetch(word)
                        progress_bar.progress((i + 1) / len(final_list))
                    
                    status.update(label="✅ 全部入库完成！", state="complete")
                    
                    if final_list:
                        st.success(f"成功存入 {len(final_list)} 个新词！")
                        st.write(f"包含: {', '.join(final_list)}")
                    else:
                        st.warning("生成的单词你好像都学过了！试试换个更偏门的场景？")

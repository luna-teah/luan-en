import streamlit as st
import utils

st.set_page_config(page_title="扩词", layout="wide")
utils.local_css()

if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")
st.title("🚀 智能扩词")

tab1, tab2 = st.tabs(["查单词", "批量生成"])

with tab1:
    w = st.text_input("输入单词")
    if st.button("🔍 查询") and w:
        with st.spinner("AI 正在深度解析..."):
            d = utils.smart_fetch(w)
        if d: 
            st.success(f"✅ {d['word']} 已入库！")
            st.json(d) # 展示所有新字段

with tab2:
    t = st.text_input("输入场景 (如: 展会 / 索赔)")
    if st.button("✨ 生成") and t:
        with st.status("AI 生成中...") as s:
            lst = utils.batch_gen(t)
            s.write(f"生成词表: {lst}")
            for word in lst: 
                utils.smart_fetch(word)
            s.update(label="✅ 入库完成！", state="complete")

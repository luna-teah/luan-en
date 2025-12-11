import streamlit as st
import utils

st.set_page_config(page_title="扩词", layout="wide")
utils.local_css()

st.title("🚀 智能扩词")
if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")

tab1, tab2 = st.tabs(["查单词", "批量生成"])

with tab1:
    w = st.text_input("输入单词")
    if st.button("🔍 查询") and w:
        with st.spinner("AI 生成中..."):
            d = utils.smart_fetch(w)
        if d: st.success("已入库！"); st.json(d)

with tab2:
    t = st.text_input("输入场景 (如: 机场)")
    if st.button("✨ 生成") and t:
        with st.status("生成中...") as s:
            lst = utils.batch_gen(t)
            s.write(f"词表: {lst}")
            for word in lst: utils.smart_fetch(word)
            s.update(label="完成！", state="complete")
        st.success("批量入库完成！")

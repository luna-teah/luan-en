import streamlit as st
import utils

st.set_page_config(page_title="扩充词库", layout="wide")
utils.local_css()

st.title("🚀 智能扩词")
if st.button("⬅️ 返回主页"): st.switch_page("app_v6.py")

tab1, tab2 = st.tabs(["查单词", "批量生成"])

with tab1:
    w = st.text_input("输入单词")
    if st.button("🔍 查询"):
        if w:
            with st.spinner("AI 正在生成..."):
                d = utils.smart_fetch(w)
            if d: 
                st.success(f"✅ {d['word']} 已入库！")
                # 简单显示结果，不显示 JSON 代码
                st.markdown(f"**含义:** {d.get('meaning')}")
                st.markdown(f"**脑洞:** {d.get('mnemonic')}")

with tab2:
    st.info("💡 提示：DeepSeek 必须有余额才能使用此功能")
    t = st.text_input("输入场景 (如: 机场 / 吵架)")
    if st.button("✨ 批量生成"):
        if t:
            with st.status("正在生成...") as s:
                lst = utils.batch_gen(t)
                if not lst:
                    s.update(label="生成失败，请检查余额", state="error")
                else:
                    s.write(f"找到词汇: {lst}")
                    for word in lst: 
                        utils.smart_fetch(word)
                    s.update(label="✅ 全部入库完成！", state="complete")
                    st.success("快去学习页面刷新看看吧！")

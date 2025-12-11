import streamlit as st
import utils

st.set_page_config(page_title="扩充词库", page_icon="🚀", layout="wide")
utils.local_css()

st.title("🚀 智能扩词")
if st.button("⬅️ 回到主页"): st.switch_page("app_v6.py")

tab1, tab2 = st.tabs(["单次查询", "批量生成"])

with tab1:
    word = st.text_input("输入单词 (例如: negotiation)", key="search")
    if st.button("🔍 查询入库"):
        if word:
            with st.spinner("AI 正在生成..."):
                data = utils.smart_fetch_word(word)
            if data:
                st.success(f"✅ {data['word']} 已保存！")
                st.json(data)

with tab2:
    st.info("输入场景，AI 自动生成 10 个相关词。")
    topic = st.text_input("场景 (例如: 机场 / 吵架 / 商务邮件)")
    if st.button("✨ 批量生成"):
        if topic:
            # 这里调用简单的prompt，直接存库
            st.warning("⚠️ 请确保 DeepSeek 有余额，否则无法生成。")
            with st.status("正在生成...") as status:
                # 简单调用 logic
                ai = utils.get_ai_client()
                if ai:
                    try:
                        prompt = f"列出10个关于'{topic}'的核心英文单词，只返回纯单词数组，如 ['word1', 'word2']"
                        resp = ai.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        import json
                        words = json.loads(resp.choices[0].message.content)
                        status.write(f"找到: {words}")
                        for w in words:
                            utils.smart_fetch_word(w) # 逐个入库
                        status.update(label="完成！", state="complete")
                    except Exception as e:
                        st.error(f"出错: {e}")

# ... (前略)
def local_css():
    st.markdown("""
    <style>
    /* 强制全局深色文字 */
    h1, h2, h3, p, div, span, label, li { color: #1F2937 !important; font-family: sans-serif; }
    .stApp { background-color: #F3F4F6; }
    /* ...其他样式... */
    </style>
    """, unsafe_allow_html=True)
# ... (后略)

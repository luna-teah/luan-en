import streamlit as st
import utils
import ast

st.set_page_config(page_title="Learn", layout="wide")
utils.local_css()

if 'logged_in' not in st.session_state or not st.session_state['logged_in']:
    st.warning("Please login first")
    st.stop()

user = st.session_state['username']
db = utils.get_db()

if st.button("Back Home"): st.switch_page("app_v6.py")
st.title("Learn New Words")

all_words = list(db.library.find({}))
u_prog = db.users.find_one({"_id": user}).get('progress', {})

cats = {}
for w in all_words:
    if w['word'] not in u_prog:
        raw_cat = str(w.get('category', 'Uncategorized')).strip()
        cats[raw_cat] = cats.get(raw_cat, 0) + 1

options = ["All"] + [f"{k} ({v})" for k,v in cats.items()]
sel = st.selectbox("Select Category", options)
target_cat = sel.split(" (")[0] if "(" in sel else sel

pool = [w for w in all_words if w['word'] not in u_prog and (target_cat=="All" or str(w.get('category','')).strip()==target_cat)]

def format_meaning(text):
    if not text: return ""
    text = str(text).strip()
    if text.startswith("{") and "simple" in text:
        try:
            d = ast.literal_eval(text)
            return f"{d.get('simple','')}; {d.get('business','')}"
        except: return text
    return text

if not pool:
    st.success("All words learned!")
else:
    w_raw = pool[0]
    if not w_raw.get('sentences') or len(w_raw.get('sentences')) < 3:
        w = utils.smart_fetch(w_raw['word']) or w_raw
    else:
        w = w_raw

    st.markdown(f"""
<div class="word-card">
<h1 style="color:#4F46E5 !important; font-size:4rem; margin:0;">{w['word']}</h1>
<p style="color:#6B7280 !important; font-size:1.5rem; font-style:italic;">/{w.get('phonetic','...')}/</p>
<span class="tag-span">{str(w.get('category','')).strip()}</span>
</div>
""", unsafe_allow_html=True)
    
    c_audio, _ = st.columns([2, 8])
    with c_audio:
        if st.button("Play Audio", use_container_width=True): 
            utils.play_audio(w['word'])

    c1, c2 = st.columns(2)
    with c1:
        clean_mean = format_meaning(w.get('meaning'))
        st.markdown(f"""
<div class="info-box" style="border-left-color: #10B981;">
<div style="font-weight:bold; opacity:0.7;">MEANING</div>
<div style="font-size:1.2rem; font-weight:bold;">{clean_mean}</div>
</div>
""", unsafe_allow_html=True)
        
        if w.get('roots'):
            st.markdown(f"""
<div class="info-box" style="border-left-color: #F97316;">
<div style="font-weight:bold; opacity:0.7; color:#C2410C;">ROOTS</div>
<div style="color:#000000;">{w['roots']}</div>
</div>
""", unsafe_allow_html=True)

    with c2:
        if w.get('collocations'):
            cols = "".join([f"<li>{c}</li>" for c in w['collocations']])
            st.markdown(f"""
<div class="info-box" style="border-left-color: #0EA5E9;">
<div style="font-weight:bold; opacity:0.7;">PHRASES</div>
<ul style="margin:0; padding-left:20px;">{cols}</ul>
</div>
""", unsafe_allow_html=True)
            
        if w.get('mnemonic'):
            st.markdown(f"""
<div class="info-box" style="border-left-color: #6366F1;">
<div style="font-weight:bold; opacity:0.7;">TRICK</div>
<div>{w['mnemonic']}</div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("#### Sentences")
    labels = ["Simple", "Daily", "Business"]
    
    if w.get('sentences'):
        for i, s in enumerate(w['sentences']):
            label = labels[i] if i<3 else "Ex"
            c_txt, c_btn = st.columns([8, 1])
            with c_txt:
                st.markdown(f"""
<div style="background:white; border-left: 4px solid #E5E7EB; padding: 10px; margin-bottom: 5px;">
<div style="font-size:0.8rem; color:#999; font-weight:bold;">{label}</div>
<div style="font-size:1.1rem; color:#000;">{s.get('en')}</div>
<div style="font-size:0.9rem; color:#666;">{s.get('cn')}</div>
</div>
""", unsafe_allow_html=True)
            with c_btn:
                st.write(""); st.write("")
                if st.button("🔈", key=f"tts_{i}"):
                    utils.play_audio(s.get('en'))
    
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("I Learned This (Next)", type="primary", use_container_width=True):
        db.users.update_one({"_id": user}, {"$set": {f"progress.{w['word']}": {"level": 1, "next_review": utils.get_next_time(1)}}})
        utils.update_daily_activity(user)
        st.rerun()

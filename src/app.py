# src/app.py  – Streamlit web UI for FitMate
import streamlit as st, csv
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

# read assets
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID         = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

if "history" not in st.session_state:
    st.session_state.history = [{"role":"system","content":SYSTEM_PROMPT}]

def send():
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""

    # 1️⃣ RAG: query the vector store
    results = client.vector_stores.query(vector_store_id=VS_ID, query=user, top_k=3)
    context = "\n".join(d.text for d in results.data)

    # 2️⃣ Chat completion
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role":"system","content":SYSTEM_PROMPT + "\n\nContext:\n" + context},
            {"role":"user","content":user}
        ]
    )
    answer = resp.choices[0].message.content

    # add to history
    st.session_state.history.append({"role":"user","content":user})
    st.session_state.history.append({"role":"assistant","content":answer})

    # log
    with open("chat_log.csv","a",newline="") as f:
        csv.writer(f).writerow([datetime.utcnow(), user, answer])

# render chat
for msg in st.session_state.history[1:]:
    st.chat_message(msg["role"]).write(msg["content"])

st.text_input("Ask FitMate …", key="msg", on_change=send)

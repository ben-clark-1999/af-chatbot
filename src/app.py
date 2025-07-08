# src/app.py  – Streamlit web UI for FitMate
import streamlit as st, csv, re, time
from datetime import datetime

from dotenv import load_dotenv
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])




import os
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(var, None)          # strip Cloud’s proxy vars





load_dotenv()


# read assets
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID         = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant", "content": "Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance."}
    ]


def send():
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""

    st.session_state.history.append({"role": "user", "content": user})

    if "thread_id" not in st.session_state:
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user,
    )

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=open("ids/af_assistant_id.txt").read().strip()
    )

    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id,
            run_id=run.id
        )

    msgs = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    assistant_msg = msgs.data[-1].content[0].text.value
    assistant_msg = re.sub(r"【[^】]*】", "", assistant_msg).strip()

    st.session_state.history.append({"role": "assistant", "content": assistant_msg})

    # Save to in-memory log
    if "log" not in st.session_state:
        st.session_state.log = []
    st.session_state.log.append({
        "timestamp": str(datetime.utcnow()),
        "user": user,
        "assistant": assistant_msg
    })

    # Save to CSV file
    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerow([datetime.utcnow(), user, assistant_msg])
    print(f"✅ Logged to {log_path}")

# render chat
# render chat
for i, msg in enumerate(st.session_state.history[1:]):
    if msg["role"] == "assistant" and i == len(st.session_state.history[1:]) - 1:
        # simulate typing for the latest assistant message
        placeholder = st.chat_message("assistant").empty()
        full_msg = msg["content"]
        animated = ""
        for char in full_msg:
            animated += char
            placeholder.markdown(animated)
            time.sleep(0.01)  # typing speed (seconds per character)
    else:
        st.chat_message(msg["role"]).write(msg["content"])


st.text_input("Ask FitMate …", key="msg", on_change=send)


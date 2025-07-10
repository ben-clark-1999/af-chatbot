# ── FitMate – Streamlit Chat App (Polished UI) ────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── Markdown-safe escape ───────────────────────────────────────────────────────
def escape_md(text: str) -> str:
    return re.sub(r'(?<!\\)([*_])', r'\\\1', text)

# ── Load env vars ─────────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing. Add it to .env or Streamlit secrets.")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ── Optional: clean proxy vars ────────────────────────────────────────────────
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(var, None)

# ── Streamlit page setup ──────────────────────────────────────────────────────
st.set_page_config(page_title="FitMate", page_icon="💜", layout="centered")

# ── Custom styling ────────────────────────────────────────────────────────────
st.markdown("""
<style>
body {
    background: linear-gradient(135deg, #eef4ff, #f9f5ff, #e0f2fe);
    background-attachment: fixed;
    font-family: 'Inter', sans-serif;
}
#MainMenu, footer {visibility: hidden;}
.chat-card {
    background: rgba(255,255,255,0.6);
    border: 1px solid rgba(255,255,255,0.3);
    backdrop-filter: blur(14px);
    border-radius: 18px;
    padding: 2rem;
    box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    max-width: 720px;
    margin: 2rem auto;
}
.assistant-msg {
    background: #ffffff;
    padding: 0.9rem 1.2rem;
    margin-bottom: 1rem;
    border-radius: 12px 12px 12px 0px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}
.user-msg {
    background: #dbeafe;
    padding: 0.9rem 1.2rem;
    margin-bottom: 1rem;
    border-radius: 12px 12px 0px 12px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    text-align: right;
}
</style>
""", unsafe_allow_html=True)

# ── Load system prompt & init session state ───────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID = open("ids/vector_store_id.txt").read().strip()

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "assistant",
            "content": "Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance.",
        },
    ]

# ── Chat handler ──────────────────────────────────────────────────────────────
def send():
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""
    st.session_state.history.append({"role": "user", "content": user})

    if "thread_id" not in st.session_state:
        thread = openai_client.beta.threads.create()
        st.session_state.thread_id = thread.id

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id, role="user", content=user
    )
    run = openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=open("ids/af_assistant_id.txt").read().strip(),
    )

    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, run_id=run.id
        )

    msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    reply = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()
    st.session_state.history.append({"role": "assistant", "content": reply})

    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, reply])

# ── Chat UI ───────────────────────────────────────────────────────────────────
st.markdown("<div class='chat-card'>", unsafe_allow_html=True)

for i, msg in enumerate(st.session_state.history[1:]):
    role = msg["role"]
    cls = "assistant-msg" if role == "assistant" else "user-msg"

    if role == "assistant" and i == len(st.session_state.history[1:]) - 1:
        placeholder = st.empty()
        animated = ""
        for ch in msg["content"]:
            animated += ch
            placeholder.markdown(f"<div class='{cls}'>{escape_md(animated)}</div>", unsafe_allow_html=True)
            time.sleep(0.01)
    else:
        st.markdown(f"<div class='{cls}'>{escape_md(msg['content'])}</div>", unsafe_allow_html=True)

st.text_input("Ask FitMate …", key="msg", on_change=send, placeholder="Type your question here…")

st.markdown("</div>", unsafe_allow_html=True)

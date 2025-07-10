# ── IMPORTS ────────────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── HELPERS ────────────────────────────────────────────────────────────────
def escape_md(text: str) -> str:
    """Back-slash stray * or _ so Markdown shows them literally."""
    return re.sub(r'(?<!\\)([*_])', r'\\\\\1', text)

# ── ENV / SECRETS ──────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError(
        "❌ OPENAI_API_KEY is missing.\n"
        "  • Locally: add it to .env\n"
        "  • Streamlit Cloud: add it in Settings → Secrets"
    )

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# Strip proxy vars
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(var, None)

# ── STREAMLIT PAGE INIT ─────────────────────────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

# Custom background gradient (light version, similar to portfolio)
st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] > .main {
        background: linear-gradient(to bottom right, #faf5ff, #ffffff, #ebf8ff);
        background-attachment: fixed;
        color: #333;
        font-family: 'Segoe UI', sans-serif;
    }
    [data-testid="stChatMessage"] .stMarkdown {
        border-radius: 1.25rem;
        padding: 0.75rem 1rem;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.45;
    }
    [data-testid="stChatMessage"].assistant .stMarkdown {
        margin-right: auto;
        background: rgba(255, 255, 255, 0.75);
        color: #111;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
        backdrop-filter: blur(8px);
    }
    [data-testid="stChatMessage"].user .stMarkdown {
        margin-left: auto;
        background: linear-gradient(135deg, #a78bfa, #6366f1);
        color: white;
        box-shadow: 0 1px 4px rgba(0,0,0,0.12);
    }
    button[kind="secondary"] div {color: inherit !important;}
    [data-testid="stChatInput"] {
        background: white;
        border-radius: 1rem;
        border: 1px solid #ddd;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    [data-testid="stChatInput"] textarea {
        padding: 0.6rem 1rem;
        min-height: 46px;
        font-size: 0.9rem;
        color: #222;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session
if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "assistant",
            "content": "Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance."
        },
    ]

# ── CHAT HANDLER ─────────────────────────────────────────────────────────────
def send() -> None:
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""
    st.session_state.history.append({"role": "user", "content": user})

    if "thread_id" not in st.session_state:
        thread = openai_client.beta.threads.create()
        st.session_state.thread_id = thread.id

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user,
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
    assistant_msg = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()
    st.session_state.history.append({"role": "assistant", "content": assistant_msg})

    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, assistant_msg])
    print(f"✅ Logged to {log_path}")

# ── CHAT UI ──────────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.history[1:]):
    is_latest_assistant = msg["role"] == "assistant" and i == len(st.session_state.history[1:]) - 1
    if is_latest_assistant:
        placeholder = st.chat_message("assistant").empty()
        animated = ""
        for ch in msg["content"]:
            animated += ch
            placeholder.markdown(escape_md(animated))
            time.sleep(0.01)
    else:
        st.chat_message(msg["role"]).markdown(escape_md(msg["content"]))

# ── CHAT INPUT ─────────────────────────────────────────────────────────────
prompt = st.chat_input("Ask FitMate …")
if prompt is not None:
    st.session_state.msg = prompt
    send()

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

# 1️⃣ local .env for dev
load_dotenv()

# 2️⃣ read secrets (cloud) → fallback to env (local)
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))

if not OPENAI_API_KEY:
    raise RuntimeError(
        "❌ OPENAI_API_KEY is missing.\n"
        "  • Locally: add it to .env\n"
        "  • Streamlit Cloud: add it in Settings → Secrets"
    )

openai_client = OpenAI(api_key=OPENAI_API_KEY)

# (optional) strip any proxy vars that might slow things down
for var in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(var, None)

# ── STREAMLIT PAGE INIT ─────────────────────────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")

st.markdown("""
    <style>
    html, body, [data-testid="stAppViewContainer"] > .main {
        background-color: #0c0c10;
        display: flex;
        justify-content: center;
        padding-top: 2rem;
    }
    .chat-phone {
        width: 390px;
        border: 1px solid #2a2d34;
        border-radius: 20px;
        background: #111317;
        box-shadow: 0 4px 16px rgba(0,0,0,0.5);
        overflow: hidden;
        padding: 0;
    }
    .chat-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 12px 16px;
        font-size: 14px;
        font-weight: 600;
        color: #f1f5f9;
        background: #111317;
        border-bottom: 1px solid #2a2d34;
    }
    .chat-header .icons {
        color: #cbd5e1;
        font-size: 18px;
    }

    [data-testid="stChatMessage"] .stMarkdown {
        border-radius: 16px;
        padding: 0.75rem 1rem;
        max-width: 85%;
        font-size: 0.95rem;
        line-height: 1.45;
    }
    [data-testid="stChatMessage"].assistant .stMarkdown {
        margin-right: auto;
        background: #1c1e24;
        color: #f3f4f6;
        border: 1px solid #2a2d34;
    }
    [data-testid="stChatMessage"].user .stMarkdown {
        margin-left: auto;
        background: #ff5c00;
        color: #fff;
    }

    [data-testid="stChatInput"] {
        background: #111317;
        border-top: 1px solid #2a2d34;
        border-radius: 0;
    }
    [data-testid="stChatInput"] textarea {
        background: transparent;
        color: #f3f4f6;
    }
    button[kind="secondary"] {
        background: #23262e;
        border: none;
    }
    button[kind="secondary"]:hover {
        background: #2d3038;
    }
    </style>
""", unsafe_allow_html=True)

with st.container():
    st.markdown('<div class="chat-phone">', unsafe_allow_html=True)
    st.markdown('<div class="chat-header">FitMate • AI Agent <span class="icons">⋮</span></div>', unsafe_allow_html=True)
    st.title("")  # blank title for spacing

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "assistant",
            "content": "Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance.",
        },
    ]

# ── CHAT HANDLER ─────────────────────────────────────────────────────────────
def send() -> None:
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""
    st.session_state.history.append({"role": "user", "content": user})

    # ① create / reuse Assistant thread
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

    # ② poll until GPT is done
    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, run_id=run.id
        )

    # ③ fetch Assistant reply
    msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    assistant_msg = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()
    st.session_state.history.append({"role": "assistant", "content": assistant_msg})

    # ④ append to local CSV (persists only on your machine / session)
    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, assistant_msg])
    print(f"✅ Logged to {log_path}")

# ── CHAT UI ──────────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.history[1:]):
    if msg["role"] == "assistant" and i == len(st.session_state.history[1:]) - 1:
        placeholder = st.chat_message("assistant").empty()
        animated = ""
        for ch in msg["content"]:
            animated += ch
            placeholder.markdown(escape_md(animated))
            time.sleep(0.01)
    else:
        st.chat_message(msg["role"]).markdown(escape_md(msg["content"]))

# ── CHAT INPUT ─────────────────────────────────────────────────────────────
prompt = st.chat_input("Type a message…")
if prompt is not None:
    st.session_state.msg = prompt
    send()


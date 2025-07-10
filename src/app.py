"""FitMate – Anytime Fitness Assistant
===================================
A single‑file Streamlit app that talks to an OpenAI Assistant and logs every
conversation locally.  This version focuses purely on *presentation polish* –
leaving all business logic untouched – so you can demo or pitch it straight to
Anytime Fitness decision‑makers.
"""

# ── IMPORTS ────────────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── HELPERS ────────────────────────────────────────────────────────────────

def escape_md(text: str) -> str:
    """Back‑slash stray * or _ so Markdown renders them literally."""
    return re.sub(r"(?<!\\)([*_])", r"\\\\\1", text)

# ── ENV / SECRETS ──────────────────────────────────────────────────────────

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

# ── STREAMLIT PAGE CONFIG ─────────────────────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID         = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")

# ── STYLE INJECTION ───────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    /* Hide default header, footer & menu */
    header[data-testid="stHeader"], #MainMenu, footer {visibility:hidden;}

    /* Compact top padding */
    [data-testid="stAppViewContainer"] > .main {padding-top:1rem;}

    /* Chat bubble base */
    [data-testid="stChatMessage"]            {padding:0;}
    [data-testid="stChatMessage"] .stMarkdown{
        border-radius:1.25rem;
        padding:0.75rem 1rem;
        max-width:85%;
        font-size:0.95rem;
        line-height:1.45;
    }

    /* Assistant bubble (left, light) */
    [data-testid="stChatMessage"].assistant .stMarkdown{
        margin-right:auto;
        margin-left :0;
        background   :#f5f5f5;
        color        :#333;
        box-shadow   :0 1px 4px rgba(0,0,0,0.06);
    }

    /* User bubble (right, gradient) */
    [data-testid="stChatMessage"].user .stMarkdown{
        margin-left :auto;
        margin-right:0;
        background  :linear-gradient(135deg,#8f5bea,#6a39d7);
        color       :#fff;
        box-shadow  :0 1px 4px rgba(0,0,0,0.12);
    }

    /* Keep "Send" visible on hover */
    button[kind="secondary"] div {color:inherit !important;}

    /* Chat input polish */
    [data-testid="stChatInput"]{background:#fff;border-radius:1rem;}
    [data-testid="stChatInput"] textarea{
        padding:0.6rem 1rem;
        min-height:46px;
        font-size:0.9rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── STATE INITIALISATION ──────────────────────────────────────────────────

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role"   : "assistant",
            "content": (
                "Hi! I'm FitMate 👋\n\n"
                "Ask me anything about Anytime Fitness — locations, billing, gym hours — "
                "or general fitness guidance."
            ),
        },
    ]

# ── CHAT BACKEND ───────────────────────────────────────────────────────────

def send() -> None:
    """Handle a user message → call Assistant → wait for run → append both sides to history."""

    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""  # clear input

    # ① create / reuse Assistant thread
    if "thread_id" not in st.session_state:
        thread = openai_client.beta.threads.create()
        st.session_state.thread_id = thread.id

    # ② Add message to thread
    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user,
    )

    # ③ Start run
    run = openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=open("ids/af_assistant_id.txt").read().strip(),
    )

    # ④ Wait until run is complete
    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id,
            run_id=run.id,
        )

    # ⑤ Fetch assistant reply
    msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id,
        order="asc",
    )
    assistant_msg = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()

    # ⑥ Append both user and assistant messages to local history
    st.session_state.history.append({"role": "user", "content": user})
    st.session_state.history.append({"role": "assistant", "content": assistant_msg})

    # ⑦ Log locally
    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, assistant_msg])
    print(f"✅ Logged to {log_path}")


# ── CHAT UI RENDER ─────────────────────────────────────────────────────────

for i, msg in enumerate(st.session_state.history[1:]):  # skip system prompt
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
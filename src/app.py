# ── top of app.py ────────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
import streamlit.components.v1 as components


def escape_md(text: str) -> str:
    """Back-slash stray * or _ so Markdown shows them literally."""
    return re.sub(r'(?<!\\)([*_])', r'\\\1', text)

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
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
):
    os.environ.pop(var, None)

# ── STREAMLIT PAGE INIT ─────────────────────────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

# 💄 Custom CSS for send button
st.markdown("""
    <style>
    div[data-testid="column"] button[kind="secondary"] {
        border-radius: 999px;
        background-color: #f0f0f0;
        color: #000;
        width: 42px;
        height: 42px;
        padding: 0;
        font-size: 1.2rem;
    }
    div[data-testid="column"] button[kind="secondary"]:hover {
        background-color: #e0e0e0;
    }
    input[type="text"] {
        border-radius: 12px;
    }
    </style>
""", unsafe_allow_html=True)

# Session history
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
    user = st.session_state.get("msg", "").strip()
    if not user:
        return

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

    # ④ log it
    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, assistant_msg])
    print(f"✅ Logged to {log_path}")

    # 🧹 rerun to reset the input safely
    st.session_state.msg = ""
    st.experimental_rerun()

# ── INPUT BOX + BUTTON ───────────────────────────────────────────────────────
with st.container():
    cols = st.columns([0.9, 0.1])
    with cols[0]:
        st.text_input("Ask FitMate …", key="msg", label_visibility="collapsed")
    with cols[1]:
        if st.button("➤", key="send_btn", help="Send"):
            send()

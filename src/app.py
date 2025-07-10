# ── FitMate – Streamlit Chat App ─────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── Helper: escape stray Markdown markers ────────────────────────────────────
import re
def escape_md(text: str) -> str:
    return re.sub(r'(?<!\\)([*_])', r'\\\1', text)

# ── ENV & OpenAI setup ───────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing in .env or Streamlit secrets.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ── Page config + custom CSS theme ───────────────────────────────────────────
st.set_page_config(
    page_title="FitMate – Anytime Fitness Assistant",
    page_icon="💜",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Glass-morphism & gradient backdrop
st.markdown(
    """
    <style>
    /* Gradient background */
    body {
      background: linear-gradient(135deg, #f9f5ff 0%, #eef4ff 25%, #ecfdf5 60%, #e0f2fe 100%);
      background-attachment: fixed;
      font-family: "Inter", sans-serif;
    }
    /* Hide default Streamlit header & footer */
    #MainMenu, footer {visibility: hidden;}

    /* Chat card */
    .glass {
      background: rgba(255,255,255,0.55);
      box-shadow: 0 8px 32px rgba(31, 38, 135, 0.1);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.18);
      border-radius: 18px;
      padding: 2rem 2.5rem;
    }

    /* Chat bubbles */
    .bubble-user {
      background: #d9e8ff;
      color: #111;
      border-radius: 18px 18px 0 18px;
      padding: .6rem .9rem;
      margin-bottom: .4rem;
      display: inline-block;
      max-width: 90%%;
    }
    .bubble-assistant {
      background: #ffffff;
      color: #111;
      border-radius: 18px 18px 18px 0;
      padding: .6rem .9rem;
      margin-bottom: .4rem;
      display: inline-block;
      max-width: 90%%;
    }

    /* Typing dots */
    @keyframes blink {
      0%% {opacity: .2;}
      20%% {opacity: 1;}
      100%% {opacity: .2;}
    }
    .typing-dot {
      height: 6px; width: 6px; margin: 0 2px;
      background: #a855f7; border-radius: 50%%; display: inline-block;
      animation: blink 1.4s infinite both;
    }
    .typing-dot:nth-child(2){animation-delay: .2s}
    .typing-dot:nth-child(3){animation-delay: .4s}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Load prompts ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
st.session_state.setdefault(
    "history",
    [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "assistant",
            "content": (
                "Hi! I'm FitMate 👋\n\n"
                "Ask me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance."
            ),
        },
    ],
)
# Vector store + assistant IDs if you use them
ASSISTANT_ID = open("ids/af_assistant_id.txt").read().strip()

# ── Chat handler ─────────────────────────────────────────────────────────────
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
        thread_id=st.session_state.thread_id, role="user", content=user
    )
    run = openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id, assistant_id=ASSISTANT_ID
    )

    # Typing indicator placeholder
    typing_box = st.empty()
    with typing_box.container():
        st.markdown(
            '<div class="bubble-assistant">'
            '<span class="typing-dot"></span><span class="typing-dot"></span><span class="typing-dot"></span>'
            '</div>',
            unsafe_allow_html=True,
        )

    while run.status in {"queued", "in_progress"}:
        time.sleep(0.35)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, run_id=run.id
        )

    msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    reply = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()
    typing_box.empty()  # remove typing indicator
    st.session_state.history.append({"role": "assistant", "content": reply})

    # Log locally
    os.makedirs("logs", exist_ok=True)
    with open("logs/chat_log.csv", "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, reply])

# ── UI ───────────────────────────────────────────────────────────────────────
st.markdown("<div class='glass'>", unsafe_allow_html=True)

for msg in st.session_state.history[1:]:
    is_user = msg["role"] == "user"
    bubble_class = "bubble-user" if is_user else "bubble-assistant"
    st.markdown(
        f"<div class='{bubble_class}'>{escape_md(msg['content'])}</div>",
        unsafe_allow_html=True,
    )

st.text_input("Ask FitMate …", key="msg", on_change=send, placeholder="Type a question…")

st.markdown("</div>", unsafe_allow_html=True)

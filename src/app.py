# ── FitMate ▸ app.py ────────────────────────────────────────────────────────
import os, csv, re, time, itertools          # ←➊ added itertools
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


# ── helpers ────────────────────────────────────────────────────────────────
def escape_md(txt: str) -> str:
    """Back-slash stray * / _ so Markdown shows them literally."""
    return re.sub(r"(?<!\\)([*_])", r"\\\1", txt)


def call_assistant(user_msg: str, ph) -> str:        # ←➋ now receives placeholder
    """
    Hit Assistants API → return plain-text reply.
    While waiting, animate dots inside `ph`.
    """
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = openai_client.beta.threads.create().id

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id, role="user", content=user_msg
    )
    run = openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=open("ids/af_assistant_id.txt").read().strip(),
    )

    # 🟣 typing-dots animation
    dots = itertools.cycle(["․", "․․", "․․․"])   # thin dots to minimise jump
    while run.status in {"queued", "in_progress"}:
        ph.markdown(f"_typing {next(dots)}_")
        time.sleep(0.35)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, run_id=run.id
        )

    msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    raw = msgs.data[-1].content[0].text.value
    return re.sub(r"【[^】]*】", "", raw).strip()


def log_interaction(q: str, a: str) -> None:
    path = "logs/chat_log.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), q, a])


# ── one-time setup ─────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing.")

for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(var, None)

openai_client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "assistant",
            "content": (
                "Hi! I'm FitMate 👋\n\n"
                "Ask me anything about Anytime Fitness — locations, billing, "
                "gym hours — or general fitness guidance."
            ),
        },
    ]

# ── show past messages ─────────────────────────────────────────────────────
for msg in st.session_state.history[1:]:
    st.chat_message(msg["role"]).markdown(escape_md(msg["content"]))

st.markdown("---")

# ── CSS for button ─────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      .animated-send{
        background:linear-gradient(135deg,#7e5bef,#5f27cd);
        color:#fff;border:none;border-radius:8px;
        font-weight:600;font-size:20px;cursor:pointer;
        width:100%;height:55px;
        transition:transform .15s,box-shadow .2s;
        box-shadow:0 4px 12px rgba(94,58,255,.3);
      }
      .animated-send:active{
        transform:scale(.93);
        box-shadow:0 2px 6px rgba(94,58,255,.6);
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── input + button (single form) ───────────────────────────────────────────
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1], gap="small")
    with col1:
        user_input = st.text_input(
            "Ask FitMate …",
            placeholder="Type your question here…",
            label_visibility="collapsed",
        )
    with col2:
        submit = st.form_submit_button("🚀", use_container_width=True, type="primary")

    # ── handle submission *inside* the form block ──────────────────────────
    if submit and user_input.strip():
        st.chat_message("user").markdown(escape_md(user_input.strip()))

        # placeholder that shows animated dots
        placeholder = st.chat_message("assistant").empty()

        # call the model (animation happens inside call_assistant)
        assistant_reply = call_assistant(user_input.strip(), placeholder)

        # stream final reply
        typed = ""
        for ch in assistant_reply:
            typed += ch
            placeholder.markdown(escape_md(typed))
            time.sleep(0.01)

        # persist + log
        st.session_state.history.extend([
            {"role": "user", "content": user_input.strip()},
            {"role": "assistant", "content": assistant_reply},
        ])
        log_interaction(user_input.strip(), assistant_reply)

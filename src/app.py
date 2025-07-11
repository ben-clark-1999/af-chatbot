# ── FitMate ▸ app.py ────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


# ── helpers ────────────────────────────────────────────────────────────────
def escape_md(txt: str) -> str:
    """Escape stray * / _ so Markdown shows them literally."""
    return re.sub(r"(?<!\\)([*_])", r"\\\1", txt)


def chat_completion(user_msg: str) -> str:
    """Call the Assistants API and return plain-text reply."""
    if "thread_id" not in st.session_state:
        st.session_state.thread_id = openai_client.beta.threads.create().id

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user_msg,
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
    raw = msgs.data[-1].content[0].text.value
    return re.sub(r"【[^】]*】", "", raw).strip()


def append_and_log(user_msg: str, assistant_msg: str) -> None:
    """Store both sides of the conversation and optionally log to CSV."""
    st.session_state.history.append({"role": "user", "content": user_msg})
    st.session_state.history.append({"role": "assistant", "content": assistant_msg})

    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user_msg, assistant_msg])


# ── one-time setup ─────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing.")

# remove any proxy vars that can slow the call down
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
            "content": "Hi! I'm FitMate 👋\n\nAsk me anything about "
                       "Anytime Fitness — locations, billing, gym hours — "
                       "or general fitness guidance."
        },
    ]

# ── chat transcript ────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.history[1:]):
    if msg["role"] == "assistant" and i == len(st.session_state.history[1:]) - 1:
        ph = st.chat_message("assistant").empty()
        buf = ""
        for ch in msg["content"]:
            buf += ch
            ph.markdown(escape_md(buf))
            time.sleep(0.01)
    else:
        st.chat_message(msg["role"]).markdown(escape_md(msg["content"]))

st.markdown("---")

# ── input + button (single form) ────────────────────────────────────────────
st.markdown(
    """
    <style>
      .animated-send {
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

with st.form(key="chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1], gap="small")

    with col1:
        user_input = st.text_input(
            "Ask FitMate …",
            placeholder="Type your question here…",
            label_visibility="collapsed",
        )

    with col2:
        submitted = st.form_submit_button("🚀", use_container_width=True,
                                          help="Send",
                                          type="primary")

    if submitted and user_input.strip():
        assistant_reply = chat_completion(user_input.strip())
        append_and_log(user_input.strip(), assistant_reply)
        # force a rerun so the new messages appear immediately
        st.experimental_rerun()

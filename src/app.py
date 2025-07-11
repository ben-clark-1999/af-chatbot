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


def process_user(user_msg: str) -> str:
    """
    ▸ Sends the user's message to OpenAI Assistants API
    ▸ Returns the assistant’s reply (plain text, no citations)
    """
    # (re-)create thread once per browser session
    if "thread_id" not in st.session_state:
        thread = openai_client.beta.threads.create()
        st.session_state.thread_id = thread.id

    # user → thread
    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user_msg,
    )

    # launch a run
    run = openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=open("ids/af_assistant_id.txt").read().strip(),
    )

    # poll until complete
    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, run_id=run.id
        )

    # assistant reply = last message in the thread
    all_msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    raw = all_msgs.data[-1].content[0].text.value
    return re.sub(r"【[^】]*】", "", raw).strip()


def send() -> None:
    """Callback shared by Enter key *and* 🚀 button."""
    txt = st.session_state.get("msg", "").strip()
    if not txt:
        return

    # add user message to history
    st.session_state.history.append({"role": "user", "content": txt})

    # fetch assistant response
    reply = process_user(txt)

    # add assistant reply to history
    st.session_state.history.append({"role": "assistant", "content": reply})

    # log locally (optional)
    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), txt, reply])

    # clear the text box for the *next* run
    st.session_state.msg = ""


# ── one-time setup ──────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing.")

# remove any proxy vars that can slow the call down
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy",
            "https_proxy", "all_proxy"):
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
    # animate ONLY the latest assistant message
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

# ── input ↔ send button row ────────────────────────────────────────────────
# CSS for a nicer, tappable button
st.markdown(
    """
    <style>
      .animated-send {
        background: linear-gradient(135deg,#7e5bef,#5f27cd);
        color:#fff;border:none;border-radius:8px;
        font-weight:600;font-size:20px;cursor:pointer;
        transition:transform .15s,box-shadow .2s;
        width:100%;height:55px;
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

col1, col2 = st.columns([5, 1], gap="small")

with col1:
    # • pressing **Enter** triggers send()
    st.text_input(
        "Ask FitMate …",
        key="msg",
        placeholder="Type your question here…",
        on_change=send,
    )

with col2:
    # • tapping / clicking **🚀** triggers send()
    #   (button rendered *before* text_input -> safe to touch session_state)
    st.button("🚀", key="send_btn", on_click=send, type="primary")

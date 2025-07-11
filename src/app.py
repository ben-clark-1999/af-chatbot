# ────────────────────────────────────────────────────────────────────────────
# app.py – FitMate  •  Anytime Fitness Assistant
# ────────────────────────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── helpers ────────────────────────────────────────────────────────────────
def escape_md(txt: str) -> str:
    """Back-slash stray * / _ so Markdown shows them literally."""
    return re.sub(r"(?<!\\)([*_])", r"\\\1", txt)


def call_assistant(user_msg: str) -> str:
    """Send *user_msg* ➜ Assistants API ➜ return plain-text reply."""
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
    raw = msgs.data[-1].content[0].text.value          # last assistant turn
    return re.sub(r"【[^】]*】", "", raw).strip()


def log_interaction(q: str, a: str) -> None:
    path = "logs/chat_log.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), q, a])


# ── one-time setup ──────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY is missing.")

# strip proxy vars that slow things down
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
if "greeted" not in st.session_state:   # has the greeting been animated yet?
    st.session_state.greeted = False

# ── page-wide styles ────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      /* nicer send button */
      .animated-send{
        background:linear-gradient(135deg,#7e5bef,#5f27cd);
        color:#fff;border:none;border-radius:8px;font-weight:600;
        font-size:20px;cursor:pointer;width:100%;height:55px;
        transition:transform .15s,box-shadow .2s;
        box-shadow:0 4px 12px rgba(94,58,255,.3);
      }
      .animated-send:active{
        transform:scale(.93);box-shadow:0 2px 6px rgba(94,58,255,.6);
      }
      /* wrap long lines / hyperlinks */
      [data-testid="stChatMessage"] .markdown-text-container{
        white-space:pre-wrap;word-wrap:break-word;overflow-wrap:anywhere;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── show chat history ───────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.history[1:]):   # skip system prompt
    role, content = msg["role"], msg["content"]

    # animate the very first assistant greeting once
    if idx == 0 and role == "assistant" and not st.session_state.greeted:
        ph = st.chat_message("assistant").empty()
        buf = ""
        for ch in content:
            buf += ch
            ph.markdown(escape_md(buf))
            time.sleep(0.01)
        st.session_state.greeted = True
    else:
        st.chat_message(role).markdown(escape_md(content))

st.markdown("---")

# ── input + 🚀 button (single form keeps them aligned) ──────────────────────
with st.form("chat_form", clear_on_submit=True):
    col1, col2 = st.columns([5, 1], gap="small")

    with col1:
        user_input = st.text_input(
            "Ask FitMate …",
            placeholder="Type your question here…",
            label_visibility="collapsed",
        )

    with col2:
        submitted = st.form_submit_button(
            "🚀", help="Send", type="primary", use_container_width=True
        )

    # ── on submit ───────────────────────────────────────────────────────────
    if submitted and user_input.strip():
        question = user_input.strip()

        # immediate echo of the user message
        st.chat_message("user").markdown(escape_md(question))

        # placeholder for assistant typing animation
        typing_placeholder = st.chat_message("assistant").empty()
        typing_placeholder.markdown("_typing …_")  # NB: narrow non-breaking space

        # call OpenAI → get reply
        answer = call_assistant(question)

        # type out reply char-by-char
        rendered = ""
        for ch in answer:
            rendered += ch
            typing_placeholder.markdown(escape_md(rendered))
            time.sleep(0.01)

        # save to session + optional log
        st.session_state.history.extend([
            {"role": "user", "content": question},
            {"role": "assistant", "content": answer},
        ])
        log_interaction(question, answer)

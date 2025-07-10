# ── FitMate – Streamlit Chat App ────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── Helper ──────────────────────────────────────────────────────────────────
def escape_md(text: str) -> str:
    """Back-slash any stray * or _ so Markdown renders literally."""
    return re.sub(r'(?<!\\)([*_])', r'\\\1', text)

# ── ENV & OpenAI setup ──────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing in .env or Streamlit secrets.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ── Page config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FitMate – Anytime Fitness Assistant",
    page_icon="💜",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS (gradient + glass) ───────────────────────────────────────────
st.markdown(
    """
    <style>
    /* ------------- Background ---------------------------------------------------- */
    .stApp {
      background: linear-gradient(135deg,
                 #f9f5ff 0%,   /* lavender   */
                 #eef4ff 25%,  /* powder blue*/
                 #ecfdf5 60%,  /* mint       */
                 #e0f2fe 100%  /* light sky  */);
      background-attachment: fixed;
      font-family: "Inter", sans-serif;
    }
    /* remove default Streamlit chrome */
    header, footer {visibility: hidden;}
    .block-container {padding-top: 4vh;}

    /* ------------- Chat card ----------------------------------------------------- */
    .glass{
      width:min(720px,92%);
      margin:0 auto 6vh;
      background:rgba(255,255,255,0.55);
      box-shadow:0 12px 40px rgba(31,38,135,.15);
      backdrop-filter:blur(14px);
      border:1px solid rgba(255,255,255,0.25);
      border-radius:22px;
      padding:2.2rem 2.4rem;
    }

    /* ------------- Bubbles -------------------------------------------------------- */
    .bubble-user{
      background:#dbeafe;              /* indigo-100 */
      color:#111;
      border-radius:20px 20px 4px 20px;
      padding:.7rem 1rem;
      margin:.2rem 0 1rem auto;
      max-width:85%;
      box-shadow:0 2px 6px rgba(0,0,0,.05);
    }
    .bubble-assistant{
      background:#fff;
      color:#111;
      border-radius:20px 20px 20px 4px;
      padding:.7rem 1rem;
      margin:.2rem auto 1rem 0;
      max-width:85%;
      box-shadow:0 2px 6px rgba(0,0,0,.05);
    }

    /* ------------- Typing dots ---------------------------------------------------- */
    @keyframes blink{0%{opacity:.2}20%{opacity:1}100%{opacity:.2}}
    .typing-dot{
      height:6px;width:6px;margin:0 2px;
      background:#a855f7;border-radius:50%;
      display:inline-block;
      animation:blink 1.4s infinite both;
    }
    .typing-dot:nth-child(2){animation-delay:.2s}
    .typing-dot:nth-child(3){animation-delay:.4s}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Prompts & state ----------------------------------------------------------------
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
ASSISTANT_ID = open("ids/af_assistant_id.txt").read().strip()

# ── Chat handler -------------------------------------------------------------------
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

    # --- typing indicator ---
    typing_box = st.empty()
    with typing_box.container():
        st.markdown(
            '<div class="bubble-assistant"><span class="typing-dot"></span>'
            '<span class="typing-dot"></span><span class="typing-dot"></span></div>',
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
    typing_box.empty()
    st.session_state.history.append({"role": "assistant", "content": reply})

    # local log
    os.makedirs("logs", exist_ok=True)
    with open("logs/chat_log.csv", "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, reply])

# ── UI -----------------------------------------------------------------------------
st.markdown("<div class='glass'>", unsafe_allow_html=True)

for msg in st.session_state.history[1:]:
    bubble = "bubble-user" if msg["role"] == "user" else "bubble-assistant"
    st.markdown(
        f"<div class='{bubble}'>{escape_md(msg['content'])}</div>",
        unsafe_allow_html=True,
    )

st.text_input("Ask FitMate …", key="msg", on_change=send, placeholder="Type a question…")

st.markdown("</div>", unsafe_allow_html=True)

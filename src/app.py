# ── FitMate – Anytime Fitness Chat Assistant ─────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── Helpers ─────────────────────────────────────────────────────────────────────
def escape_md(txt: str) -> str:
    return re.sub(r"(?<!\\)([*_])", r"\\\1", txt)

def render_bubble(role: str, content: str) -> str:
    icon = "🧑‍💻" if role == "user" else "🤖"
    cls  = "bubble-user" if role == "user" else "bubble-assistant"
    return (
        f"<div class='{cls}'>"
        f"<span class='icon'>{icon}</span>"
        f"<span class='txt'>{escape_md(content)}</span></div>"
    )

# ── Init: Env, OpenAI ───────────────────────────────────────────────────────────
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing in .env or Streamlit secrets.")
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FitMate – Anytime Fitness Assistant",
    page_icon="💜",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ── CSS Styling ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
.stApp {
  background: linear-gradient(135deg,#f9f5ff 0%,#eef4ff 25%,#ecfdf5 60%,#e0f2fe 100%);
  background-attachment: fixed;
  font-family: "Inter", sans-serif;
}
header,footer{visibility:hidden;}
.block-container{padding-top:4vh;}
.glass {
  width:min(720px,92%);
  margin:0 auto 6vh;
  background:rgba(255,255,255,.55);
  backdrop-filter:blur(14px);
  border:1px solid rgba(255,255,255,.25);
  border-radius:22px;
  padding:2.2rem 2.4rem;
  box-shadow:0 12px 40px rgba(31,38,135,.15);
}
.bubble-user,.bubble-assistant {
  display:flex;gap:.7rem;align-items:flex-start;
  padding:.7rem 1rem;margin:.25rem 0 1.1rem;
  max-width:90%;
  box-shadow:0 2px 6px rgba(0,0,0,.05);
  border-radius:20px 20px 4px 20px;
  color:#111;
}
.bubble-assistant {
  background:#fff;border-radius:20px 20px 20px 4px;
}
.bubble-user {
  background:#dbeafe;margin-left:auto;
}
.icon {
  font-size:1.35rem;line-height:1.35rem;
}
.txt {
  white-space:pre-wrap;
}
@keyframes blink{0%{opacity:.25}20%{opacity:1}100%{opacity:.25}}
.typing-dot {
  height:6px;width:6px;margin:0 2px;
  background:#a855f7;border-radius:50%;
  display:inline-block;
  animation:blink 1.4s infinite both;
}
.typing-dot:nth-child(2){animation-delay:.2s}
.typing-dot:nth-child(3){animation-delay:.4s}
.stButton>button {
  background: linear-gradient(90deg,#a855f7 0%,#6366f1 100%);
  border: none; color: #fff; font-weight: 600;
  font-size: 1rem; padding: .55rem 1.15rem;
  border-radius: 14px;
  transition: transform .15s ease, box-shadow .15s ease;
}
.stButton>button:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 18px rgba(99,102,241,.35);
}
.stButton>button:active {
  transform: translateY(0);
  box-shadow: 0 3px 8px rgba(0,0,0,.22);
}
</style>
""", unsafe_allow_html=True)

# ── Prompt & Assistant ─────────────────────────────────────────────────────────
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

# ── Chat handler ──────────────────────────────────────────────────────────────
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

    typing_box = st.empty()
    with typing_box.container():
        st.markdown(
            '<div class="bubble-assistant"><span class="icon">🤖</span>'
            '<span><span class="typing-dot"></span><span class="typing-dot"></span>'
            '<span class="typing-dot"></span></span></div>',
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
    reply_text = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()
    typing_box.empty()

    # ── Animated reply ──
    reveal_box = st.empty()
    animated = ""
    for ch in reply_text:
        animated += ch
        reveal_box.markdown(render_bubble("assistant", animated), unsafe_allow_html=True)
        time.sleep(0.025)
    st.session_state.history.append({"role": "assistant", "content": reply_text})

    # ── Log to file ──
    os.makedirs("logs", exist_ok=True)
    with open("logs/chat_log.csv", "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, reply_text])

# ── UI ────────────────────────────────────────────────────────────────────────
st.markdown("<div class='glass'>", unsafe_allow_html=True)

# Static bubbles (skip final assistant message if it's animating)
for i, msg in enumerate(st.session_state.history[1:]):
    is_last = i == len(st.session_state.history[1:]) - 1
    if msg["role"] == "assistant" and is_last:
        continue
    st.markdown(render_bubble(msg["role"], msg["content"]), unsafe_allow_html=True)

# Input row (text + button)
col_msg, col_btn = st.columns([0.85, 0.15])
with col_msg:
    st.text_input("", key="msg", placeholder="Type a question…", label_visibility="collapsed", on_change=send)
with col_btn:
    if st.button("Send"):
        send()

st.markdown("</div>", unsafe_allow_html=True)

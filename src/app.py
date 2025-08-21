# ── FitMate • app.py ────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI


# ── text helpers ────────────────────────────────────────────────────────────
def escape_md(txt: str) -> str:
    """Back-slash stray * or _ so Markdown shows them literally (for user msgs)."""
    return re.sub(r"(?<!\\)([*_])", r"\\\1", txt)


def clean(txt: str) -> str:
    """
    • normalises dash / hyphen weirdness that broke the cost answers
    • leaves everything else intact
    """
    txt = txt.replace("\u2011", "-")                    # non-breaking hyphen → normal
    txt = re.sub(r"[\u2013\u2014]", " — ", txt)        # en/em dash → space-dash-space
    txt = re.sub(r"\s{2,}", " ", txt)                  # collapse double spaces
    return txt.strip()


# ── OpenAI call ─────────────────────────────────────────────────────────────
def call_assistant(user_msg: str) -> str:
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

    raw = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    ).data[-1].content[0].text.value

    # Remove citations like   etc.
    raw = re.sub(r"【\d+:\d+†[^】]+】", "", raw)

    return clean(raw)


def log(q: str, a: str) -> None:
    path = "logs/chat_log.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), q, a])


# ── one-time setup ──────────────────────────────────────────────────────────
load_dotenv()
key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not key:
    raise RuntimeError("❌ OPENAI_API_KEY is missing.")
openai_client = OpenAI(api_key=key)

# Avoid proxy interference on Streamlit Cloud
for v in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
          "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(v, None)

SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant",
         "content": ("Hi! I'm FitMate 👋\n\n"
                     "Ask me anything about Anytime Fitness — locations, "
                     "billing, gym hours — or general fitness guidance.")},
    ]

# ── chat transcript ────────────────────────────────────────────────────────
for idx, msg in enumerate(st.session_state.history[1:]):
    box = st.chat_message(msg["role"])
    if (msg["role"] == "assistant"
            and idx == 0
            and not st.session_state.get("intro_done")):
        # type-once intro with Markdown (so **bold** and lists render)
        ph = box.empty()
        buf = ""
        for ch in msg["content"]:
            buf += ch
            ph.markdown(buf)
            time.sleep(0.01)
        st.session_state.intro_done = True
    else:
        if msg["role"] == "user":
            box.markdown(escape_md(msg["content"]))
        else:
            box.markdown(msg["content"])

st.markdown("---")

# ── CSS tweaks ──────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
      div.stButton > button:first-child {
        background:linear-gradient(135deg,#7e5bef,#5f27cd);
        color:#fff;border:none;border-radius:8px;
        font-weight:600;font-size:20px;cursor:pointer;
        width:100%;height:55px;
        transition:transform .15s,box-shadow .2s;
        box-shadow:0 4px 12px rgba(94,58,255,.3);
      }
      div.stButton > button:first-child:active {
        transform:scale(.93);
        box-shadow:0 2px 6px rgba(94,58,255,.6);
      }
      @keyframes pulse{0%{opacity:0}50%{opacity:1}100%{opacity:0}}
      .blinker{font-weight:600;animation:pulse 1s infinite}
    </style>
    """,
    unsafe_allow_html=True,
)

# ── input + button (single <form>) ──────────────────────────────────────────
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
            "🚀",
            use_container_width=True,
            help="Send"
        )

    if submitted and user_input.strip():
        # show user message safely (no unintended markdown)
        st.chat_message("user").markdown(escape_md(user_input.strip()))

        # temporary "typing" indicator
        ph = st.chat_message("assistant").empty()
        ph.markdown("*typing <span class='blinker'>▋</span>*", unsafe_allow_html=True)

        assistant_reply = call_assistant(user_input.strip())

        # final assistant message as Markdown (so **Gladesville** renders bold)
        ph.markdown(assistant_reply)

        # store raw user + assistant messages (we escape only when displaying user)
        st.session_state.history.extend([
            {"role": "user", "content": user_input.strip()},
            {"role": "assistant", "content": assistant_reply},
        ])
        log(user_input.strip(), assistant_reply)
        st.experimental_rerun()

# ── FitMate – Streamlit Chat (Polished) ──────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── util ---------------------------------------------------------------------
def escape_md(s: str) -> str:          # show * / _ literally
    return re.sub(r'(?<!\\)([*_])', r'\\\1', s)

def bubble(role: str, txt: str) -> str:
    icon = "🧑" if role == "user" else "🤖"
    cls  = "bubble-user" if role == "user" else "bubble-ai"
    return f"<div class='{cls}'><span class='ico'>{icon}</span>{escape_md(txt)}</div>"

# ── env / OpenAI -------------------------------------------------------------
load_dotenv()
OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not OPENAI_API_KEY:
    raise RuntimeError("❌ OPENAI_API_KEY missing in .env or Streamlit secrets.")
client = OpenAI(api_key=OPENAI_API_KEY)

# ── page & css ---------------------------------------------------------------
st.set_page_config(page_title="FitMate", page_icon="💜", layout="centered")

st.markdown(
    """
<style>
/* ---------- background ---------- */
.stApp{background:linear-gradient(135deg,#eef4ff 0%,#f9f5ff 50%,#e0f2fe 100%);
       background-attachment:fixed;font-family:"Inter","Segoe UI",sans-serif;}
#MainMenu,footer{visibility:hidden}

/* ---------- card ---------- */
.card{max-width:600px;margin:5vh auto;padding:2.2rem 2.4rem;
      background:rgba(255,255,255,.55);backdrop-filter:blur(16px);
      border:1px solid rgba(255,255,255,.3);border-radius:18px;
      box-shadow:0 12px 40px rgba(0,0,0,.08)}

/* ---------- bubbles ---------- */
.bubble-ai,.bubble-user{display:flex;gap:.6rem;padding:.7rem 1rem;
    margin:.35rem 0;box-shadow:0 2px 5px rgba(0,0,0,.05);
    border-radius:16px;white-space:pre-wrap;line-height:1.5}
.bubble-ai  {background:#ffffff;border-radius:16px 16px 16px 4px;max-width:92%}
.bubble-user{background:#dbeafe;border-radius:16px 16px 4px 16px;
             margin-left:auto;text-align:right;max-width:92%}

.ico{font-size:1.25rem}

/* ---------- Send button ---------- */
.stButton>button{width:100%;background:linear-gradient(90deg,#8b5cf6 0%,#6366f1 100%);
    border:none;color:#fff;font-weight:600;padding:.55rem 1rem;border-radius:14px;
    transition:transform .15s,box-shadow .15s}
.stButton>button:hover{transform:translateY(-2px);
    box-shadow:0 8px 22px rgba(99,102,241,.35)}
.stButton>button:active{transform:none;box-shadow:0 4px 12px rgba(0,0,0,.18)}
</style>
""",
    unsafe_allow_html=True,
)

# ── load prompts & state -----------------------------------------------------
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant",
         "content":"Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance."},
    ]

ASSISTANT_ID = open("ids/af_assistant_id.txt").read().strip()

# ── chat handler -------------------------------------------------------------
def send():
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""
    st.session_state.history.append({"role": "user", "content": user})

    if "thread" not in st.session_state:
        st.session_state.thread = client.beta.threads.create().id

    client.beta.threads.messages.create(thread_id=st.session_state.thread,
                                        role="user", content=user)
    run = client.beta.threads.runs.create(thread_id=st.session_state.thread,
                                          assistant_id=ASSISTANT_ID)

    # wait
    while run.status in {"queued","in_progress"}:
        time.sleep(0.4)
        run = client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread, run_id=run.id)

    reply = client.beta.threads.messages.list(
        thread_id=st.session_state.thread, order="asc").data[-1].content[0].text.value
    reply = re.sub(r"【[^】]*】","",reply).strip()

    # typewriter reveal
    reveal = st.empty()
    buf=""
    for ch in reply:
        buf += ch
        reveal.markdown(bubble("assistant", buf), unsafe_allow_html=True)
        time.sleep(0.02)
    st.session_state.history.append({"role":"assistant","content":reply})

    # log
    os.makedirs("logs",exist_ok=True)
    with open("logs/chat_log.csv","a",newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc),user,reply])

# ── UI -----------------------------------------------------------------------
st.markdown("<div class='card'>",unsafe_allow_html=True)

# existing history (skip typewriter)
for m in st.session_state.history[1:]:
    st.markdown(bubble(m["role"], m["content"]), unsafe_allow_html=True)

# input + button
c1,c2 = st.columns([0.78,0.22])
with c1:
    st.text_input("Ask FitMate …",key="msg",label_visibility="collapsed",
                  placeholder="Type your question here…")
with c2:
    if st.button("Send"):
        send()

st.markdown("</div>",unsafe_allow_html=True)

# ── FitMate – Streamlit Chat (refined) ───────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# ── helpers ------------------------------------------------------------------
def escape_md(s: str) -> str:
    return re.sub(r'(?<!\\)([*_])', r'\\\1', s)

def bubble(role: str, txt: str) -> str:
    ico = "🧑" if role == "user" else "🤖"
    cls = "bubble-user" if role == "user" else "bubble-ai"
    return f"<div class='{cls}'><span class='ico'>{ico}</span><span>{escape_md(txt)}</span></div>"

# ── env / OpenAI -------------------------------------------------------------
load_dotenv()
key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not key:
    raise RuntimeError("❌ OPENAI_API_KEY missing")
client = OpenAI(api_key=key)

# ── page cfg -----------------------------------------------------------------
st.set_page_config(page_title="FitMate", page_icon="💜", layout="centered")

st.markdown(
    """
<style>
/* ==== global =============================================================== */
.stApp{background:linear-gradient(135deg,#eef4ff 0%,#f9f5ff 50%,#e0f2fe 100%);
       background-attachment:fixed;font-family:"Inter",sans-serif;}
header,footer,/* default */
.viewerBadge_container__*, .stDeployButton, .stToolbar {display:none !important;}
.block-container{padding-top:4vh;}

/* ==== card ================================================================= */
.card{max-width:600px;margin:5vh auto;padding:2.1rem 2.4rem;
      background:rgba(255,255,255,.58);backdrop-filter:blur(14px);
      border:1px solid rgba(255,255,255,.3);border-radius:20px;
      box-shadow:0 10px 38px rgba(0,0,0,.08);}

/* ==== bubbles ============================================================== */
.bubble-ai,.bubble-user{display:flex;gap:.55rem;line-height:1.5;
    padding:.65rem 1rem;margin:.35rem 0;max-width:70%;white-space:pre-wrap;
    border-radius:18px;box-shadow:0 2px 5px rgba(0,0,0,.05)}
.bubble-ai{background:#fff;border-radius:18px 18px 18px 4px;}
.bubble-user{background:#4f8bfd;color:#fff;border-radius:18px 18px 4px 18px;
             margin-left:auto;flex-direction:row-reverse;text-align:right;}
.ico{font-size:1.25rem;line-height:1.25rem}

/* ==== Send button ========================================================== */
.stButton>button{width:100%;background:linear-gradient(90deg,#8b5cf6 0%,#6366f1 100%);
    color:#fff!important;font-weight:600;font-size:1rem;border:none;
    padding:.55rem 1rem;border-radius:14px;cursor:pointer;
    transition:transform .15s,box-shadow .15s}
.stButton>button:hover  {transform:translateY(-2px);
                         box-shadow:0 8px 22px rgba(99,102,241,.35);}
.stButton>button:active {transform:none;box-shadow:0 4px 12px rgba(0,0,0,.22);}
</style>
""",
    unsafe_allow_html=True,
)

# ── state --------------------------------------------------------------------
SYSTEM = open("data/af_prompt.txt").read().strip()
if "history" not in st.session_state:
    st.session_state.history = [
        {"role":"system","content":SYSTEM},
        {"role":"assistant",
         "content":"Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance."},
    ]
ASSISTANT_ID = open("ids/af_assistant_id.txt").read().strip()

# ── backend ------------------------------------------------------------------
def send():
    user = st.session_state.msg.strip()
    if not user: return
    st.session_state.msg=""
    st.session_state.history.append({"role":"user","content":user})

    if "thread" not in st.session_state:
        st.session_state.thread = client.beta.threads.create().id

    client.beta.threads.messages.create(thread_id=st.session_state.thread,
                                        role="user",content=user)
    run = client.beta.threads.runs.create(thread_id=st.session_state.thread,
                                          assistant_id=ASSISTANT_ID)
    while run.status in {"queued","in_progress"}:
        time.sleep(0.35)
        run = client.beta.threads.runs.retrieve(thread_id=st.session_state.thread,
                                                run_id=run.id)

    reply = client.beta.threads.messages.list(
        thread_id=st.session_state.thread,order="asc").data[-1].content[0].text.value
    reply = re.sub(r"【[^】]*】","",reply).strip()

    # typewriter
    reveal = st.empty()
    buf=""
    for ch in reply:
        buf+=ch
        reveal.markdown(bubble("assistant",buf),unsafe_allow_html=True)
        time.sleep(0.018)
    st.session_state.history.append({"role":"assistant","content":reply})

    # log
    os.makedirs("logs",exist_ok=True)
    with open("logs/chat_log.csv","a",newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc),user,reply])

# ── UI -----------------------------------------------------------------------
st.markdown("<div class='card'>",unsafe_allow_html=True)

for m in st.session_state.history[1:]:
    st.markdown(bubble(m["role"], m["content"]), unsafe_allow_html=True)

c1,c2 = st.columns([0.78,0.22])
with c1:
    st.text_input("Ask FitMate …",key="msg",label_visibility="collapsed",
                  placeholder="Type your question here…")
with c2:
    if st.button("Send"): send()

st.markdown("</div>",unsafe_allow_html=True)

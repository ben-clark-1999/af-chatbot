# ── top of app.py ────────────────────────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from supabase import create_client, Client

# 1️⃣ local .env for dev
load_dotenv()

# 2️⃣ read secrets (cloud) → fallback to env (local)
OPENAI_API_KEY     = st.secrets.get("OPENAI_API_KEY"    , os.getenv("OPENAI_API_KEY"))
SUPABASE_URL       = st.secrets.get("SUPABASE_URL"      , os.getenv("SUPABASE_URL"))
SUPABASE_ANON_KEY  = st.secrets.get("SUPABASE_ANON_KEY" , os.getenv("SUPABASE_ANON_KEY"))

if not all([OPENAI_API_KEY, SUPABASE_URL, SUPABASE_ANON_KEY]):
    raise RuntimeError(
        "❌ One of OPENAI_API_KEY / SUPABASE_URL / SUPABASE_ANON_KEY is missing."
        "  • Locally: add them to .env\n"
        "  • Streamlit Cloud: add them in Settings → Secrets"
    )

openai_client:   OpenAI  = OpenAI(api_key=OPENAI_API_KEY)
supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
# ─────────────────────────────────────────────────────────────────────────────

# (optional) strip any proxy vars that might slow things down
for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
            "http_proxy", "https_proxy", "all_proxy"):
    os.environ.pop(var, None)

# ── STREAMLIT PAGE INIT ─────────────────────────────────────────────────────
SYSTEM_PROMPT = open("data/af_prompt.txt").read().strip()
VS_ID         = open("ids/vector_store_id.txt").read().strip()

st.set_page_config(page_title="FitMate", page_icon="💜")
st.title("💜 FitMate – Anytime Fitness Assistant")

if "history" not in st.session_state:
    st.session_state.history = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "assistant",
         "content": "Hi! I'm FitMate 👋\n\nAsk me anything about Anytime Fitness — locations, billing, gym hours — or general fitness guidance."}
    ]

# ── CHAT HANDLER ─────────────────────────────────────────────────────────────
def send() -> None:
    user = st.session_state.msg.strip()
    if not user:
        return
    st.session_state.msg = ""
    st.session_state.history.append({"role": "user", "content": user})

    # ① create / reuse Assistant thread
    if "thread_id" not in st.session_state:
        thread = openai_client.beta.threads.create()
        st.session_state.thread_id = thread.id

    openai_client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=user,
    )
    run = openai_client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=open("ids/af_assistant_id.txt").read().strip(),
    )

    # ② poll until GPT is done
    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=st.session_state.thread_id, run_id=run.id
        )

    # ③ fetch Assistant reply
    msgs = openai_client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id, order="asc"
    )
    assistant_msg = re.sub(r"【[^】]*】", "", msgs.data[-1].content[0].text.value).strip()
    st.session_state.history.append({"role": "assistant", "content": assistant_msg})

    # ④ persist to Supabase
    try:
        supabase.table("chat_logs").insert({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user_input": user,
            "bot_response": assistant_msg
        }).execute()
    except Exception as e:
        print(f"❌ Supabase insert failed: {e}")

    # ⑤ append to local CSV (optional)
    log_path = os.path.abspath("logs/chat_log.csv")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), user, assistant_msg])
    print(f"✅ Logged to {log_path}")

# ── CHAT UI ──────────────────────────────────────────────────────────────────
for i, msg in enumerate(st.session_state.history[1:]):
    if msg["role"] == "assistant" and i == len(st.session_state.history[1:]) - 1:
        placeholder = st.chat_message("assistant").empty()
        animated = ""
        for ch in msg["content"]:
            animated += ch
            placeholder.markdown(animated)
            time.sleep(0.01)
    else:
        st.chat_message(msg["role"]).write(msg["content"])

st.text_input("Ask FitMate …", key="msg", on_change=send)

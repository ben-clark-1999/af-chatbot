# ── FitMate • app.py (multi-agent) ───────────────────────────────────────────
import os, csv, re, time
from datetime import datetime, timezone
from typing import Optional

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

from ui import inject_styles, sidebar_agent_picker, render_history



# ── helpers ──────────────────────────────────────────────────────────────────
def escape_md(txt: str) -> str:
    return re.sub(r"(?<!\\)([*_])", r"\\\1", txt)


def clean(txt: str, keep_newlines: bool = False) -> str:
    """
    Generic tidy for all agents.

    keep_newlines = True  → keep \n and only collapse extra spaces
    keep_newlines = False → old behaviour (collapses everything)
    """
    txt = txt.replace("\u2011", "-")
    txt = re.sub(r"[\u2013\u2014]", " — ", txt)

    if keep_newlines:
        # keep \n, just squash big runs of spaces/tabs
        txt = txt.replace("\r\n", "\n")
        txt = re.sub(r"[ \t]{2,}", " ", txt)
    else:
        # original behaviour
        txt = re.sub(r"\s{2,}", " ", txt)

    return txt.strip()


def normalize_workout_markdown(text: str) -> str:
    """
    Normalise training output:
    - break glued bullets
    - indent exercises
    - force tips section
    - add default tips if model forgets
    """

    # split inline bullets like "Day 1 — Push - Bench Press ..." -> 2 lines
    text = text.replace(" - ", "\n- ")

    # sometimes: "Progression: ... Tips for success:"
    text = re.sub(
        r"(Progression:[^\n]*?)\s+(Tips for success:)",
        r"\n\1\n\2",
        text,
        flags=re.IGNORECASE,
    )

    # make sure key markers start on their own line
    for pat in [
        r"(Day\s+\d+\s*[–—-]\s*)",
        r"(Exercise\s+\d+:)",
        r"(Rest:)",
        r"(Progression:)",
        r"(Tips for success:)",
    ]:
        text = re.sub(r"\s*" + pat, r"\n\1", text, flags=re.IGNORECASE)

    lines = []
    in_tips = False

    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue

        # remove weird trailing symbols
        line = re.sub(r"[-*]+$", "", line).strip()

        # remove junk like " 2." at end of a line
        line = re.sub(r"\s+\d+\.\s*$", "", line)

        # skip lonely "1." lines
        if re.match(r"^\d+\.\s*$", line):
            continue

        # start tips section
        if re.match(r"(?i)^tips for success:", line):
            lines.append("**Tips for success:**")
            in_tips = True
            continue

        if in_tips:
            # tips get different bullet
            lines.append(f"• {line}")
            continue

        # day heading
        if re.match(r"(?i)^day\s+\d+", line):
            m = re.match(r"(?i)^day\s+(\d+)\s*[–—-]?\s*(.*)", line)
            day_num = m.group(1)
            focus = m.group(2).strip()
            focus = re.sub(r"[-*]+$", "", focus).strip()
            if focus:
                lines.append(f"{day_num}. **Day {day_num} — {focus}**")
            else:
                lines.append(f"{day_num}. **Day {day_num}**")
            continue

        lower = line.lower()

        # indent workout lines
        if (
            lower.startswith("exercise ")
            or lower.startswith("rest:")
            or lower.startswith("progression:")
            or lower.startswith("- ")
        ):
            if lower.startswith("- "):
                lines.append(f"  {line}")
            else:
                lines.append(f"  - {line}")
            continue

        # fallback
        lines.append(line)

    # ── post-process: ensure tips exist ──────────────────────────────────────
    if any(l.strip().lower().startswith("**tips for success:**") for l in lines):
        out_lines = []
        i = 0
        while i < len(lines):
            out_lines.append(lines[i])
            if lines[i].strip().lower().startswith("**tips for success:**"):
                j = i + 1
                tip_count = 0
                while j < len(lines) and lines[j].startswith("• "):
                    tip_count += 1
                    j += 1
                if tip_count == 0:
                    out_lines.append("• Warm up 5–10 mins before lifting.")
                    out_lines.append("• Prioritise good form over load.")
                    out_lines.append("• Sleep 7–9 hrs and get enough protein 💪")
                out_lines.extend(lines[j:])
                return "\n".join(out_lines)
            i += 1
        return "\n".join(out_lines)
    else:
        lines.append("**Tips for success:**")
        lines.append("• Warm up 5–10 mins before lifting.")
        lines.append("• Prioritise good form over load.")
        lines.append("• Sleep 7–9 hrs and get enough protein 💪")
        return "\n".join(lines)


# ── define all agents here ───────────────────────────────────────────────────
AGENTS = {
    "general": {
        "label": "AF – Member Support",
        "id_path": "ids/af_assistant_id.txt",
        "greeting": (
            "Hi! I'm FitMate 👋\n\n"
            "Ask me anything about Anytime Fitness — locations, billing, staffed hours, or joining."
        ),
        "goals": [],
    },
    "training": {
        "label": "AF - Virtual Coach",
        "id_path": "ids/af_training_id.txt",
        "greeting": (
            "You're chatting with the training/programming coach. Tell me your goal and available days."
        ),
        "goals": ["Lose fat", "Build muscle", "Get stronger", "Improve conditioning"],
    },
    "nutrition": {
        "label": "AF – Nutrition Coach",
        "id_path": "ids/af_nutrition_id.txt",
        "greeting": (
            "You're chatting with the nutrition coach. Tell me what you eat now and your target."
        ),
        "goals": ["Lose fat", "Maintain & lean out", "Gain muscle"],
    },
}


# ── logging ──────────────────────────────────────────────────────────────────
def log(agent_key: str, q: str, a: str) -> None:
    path = "logs/chat_log.csv"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow([datetime.now(timezone.utc), agent_key, q, a])


# ── load env & client ────────────────────────────────────────────────────────
load_dotenv()
key = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
if not key:
    raise RuntimeError("❌ OPENAI_API_KEY is missing.")
openai_client = OpenAI(api_key=key)

# avoid proxy vars
for v in (
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "http_proxy",
    "https_proxy",
    "all_proxy",
):
    os.environ.pop(v, None)


# ── state helpers ────────────────────────────────────────────────────────────
def get_thread_id(agent_key: str) -> str:
    if "threads" not in st.session_state:
        st.session_state["threads"] = {}
    if agent_key not in st.session_state["threads"]:
        thread = openai_client.beta.threads.create()
        st.session_state["threads"][agent_key] = thread.id
    return st.session_state["threads"][agent_key]


def get_history(agent_key: str):
    if "histories" not in st.session_state:
        st.session_state["histories"] = {}
    if agent_key not in st.session_state["histories"]:
        st.session_state["histories"][agent_key] = [
            {"role": "assistant", "content": AGENTS[agent_key]["greeting"]}
        ]
    return st.session_state["histories"][agent_key]


def set_history(agent_key: str, history):
    if "histories" not in st.session_state:
        st.session_state["histories"] = {}
    st.session_state["histories"][agent_key] = history


def load_assistant_id(path: str) -> str:
    with open(path) as f:
        return f.read().strip()


# ── core call ────────────────────────────────────────────────────────────────
def call_assistant(user_msg: str, agent_key: str, goal: Optional[str] = None) -> str:
    thread_id = get_thread_id(agent_key)
    assistant_id = load_assistant_id(AGENTS[agent_key]["id_path"])

    if goal:
        user_msg = f"User goal: {goal}\n\n{user_msg}"

    openai_client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_msg,
    )

    run = openai_client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=assistant_id,
    )

    while run.status in {"queued", "in_progress"}:
        time.sleep(0.4)
        run = openai_client.beta.threads.runs.retrieve(
            thread_id=thread_id,
            run_id=run.id,
        )

    raw = openai_client.beta.threads.messages.list(
        thread_id=thread_id,
        order="asc",
    ).data[-1].content[0].text.value

    # strip vector-store-style citations like 
    raw = re.sub(r"【\d+:\d+†[^】]+】", "", raw)

    # 👇 nutrition keeps newlines
    keep_newlines = agent_key == "nutrition"
    raw = clean(raw, keep_newlines=keep_newlines)

    if agent_key == "training":
        raw = normalize_workout_markdown(raw)

    return raw


# ── UI ───────────────────────────────────────────────────────────────────────
import streamlit as st

st.set_page_config(page_title="FitMate", page_icon="💜")

# use the sidebar from ui.py
agent_key, selected_goal = sidebar_agent_picker(AGENTS)

st.title("💜 FitMate – Anytime Fitness Assistant (multi-agent)")

# show chat history for the chosen agent
history = get_history(agent_key)
render_history(history, escape_md)

st.markdown("---")

# global styles
inject_styles()

# chat form
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
            help="Send",
        )

    if submitted and user_input.strip():
        st.chat_message("user").markdown(escape_md(user_input.strip()))

        ph = st.chat_message("assistant").empty()
        ph.markdown("*typing …*", unsafe_allow_html=True)

        reply = call_assistant(user_input.strip(), agent_key, goal=selected_goal)

        # render assistant reply with line breaks
        ph.markdown(reply, unsafe_allow_html=True)

        history.append({"role": "user", "content": user_input.strip()})
        history.append({"role": "assistant", "content": reply})
        set_history(agent_key, history)

        log(agent_key, user_input.strip(), reply)

        st.rerun()

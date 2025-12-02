# ui.py
from typing import Any, Dict, List, Optional
import streamlit as st


def inject_styles() -> None:
    """Global CSS for buttons / layout."""
    st.markdown(
        """
        <style>
          /* send button */
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

          /* optional: narrow main chat width */
          .block-container {
            max-width: 950px;
            margin: 0 auto;
          }
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_agent_picker(agents: Dict[str, Dict[str, Any]]):
    """Shows the sidebar and returns (agent_key, selected_goal or None)."""
    with st.sidebar:
        st.header("FitMate agents")

        agent_key = st.selectbox(
            "Choose an agent:",
            options=list(agents.keys()),
            format_func=lambda k: agents[k]["label"],
        )
        current_agent = agents[agent_key]

        selected_goal: Optional[str] = None
        if current_agent.get("goals"):
            goal_option = st.selectbox(
                "Goal (optional):",
                options=["(not specified)"] + current_agent["goals"],
            )
            if goal_option != "(not specified)":
                selected_goal = goal_option

    return agent_key, selected_goal


def render_history(history: List[Dict[str, str]], escape_md) -> None:
    """Renders the chat messages for the current agent."""
    for msg in history:
        box = st.chat_message(msg["role"])
        if msg["role"] == "user":
            # keep your escaping for user text
            box.markdown(escape_md(msg["content"]))
        else:
            # allow markdown/HTML-looking content from assistants
            box.markdown(msg["content"], unsafe_allow_html=True)



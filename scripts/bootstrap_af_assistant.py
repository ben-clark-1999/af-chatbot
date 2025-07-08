#!/usr/bin/env python
# scripts/bootstrap_af_assistant.py
#
# 1.  Creates a brand-new vector store
# 2.  Uploads and indexes data/club_directory.txt into that store
# 3.  Builds a GPT-4o assistant wired to the store via the File-Search tool
# 4.  Persists the new IDs to ids/vector_store_id.txt and ids/af_assistant_id.txt
#
# Run:  python scripts/bootstrap_af_assistant.py

from __future__ import annotations
from openai import OpenAI
from dotenv import load_dotenv
from pathlib import Path
import os
import time

load_dotenv()                    # picks up OPENAI_API_KEY from .env or env-vars
client = OpenAI()                # uses the key automatically

# ───────────────────────────────────────────────────────────────────────────────
# 1.  Create vector store and upload club directory
# ───────────────────────────────────────────────────────────────────────────────
print("🚀  Creating vector store …")
vs = client.vector_stores.create(name="AF-clubs")
vs_id = vs.id

print("📤  Uploading club_directory.txt and waiting for indexing …")
client.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vs_id,
    files=[open("data/club_directory.txt", "rb")],
)
print("✅  Vector store ready:", vs_id)

# ───────────────────────────────────────────────────────────────────────────────
# 2.  Load the system prompt
# ───────────────────────────────────────────────────────────────────────────────
prompt = Path("data/af_prompt.txt").read_text()

# ───────────────────────────────────────────────────────────────────────────────
# 3.  Create the assistant wired to this vector store
# ───────────────────────────────────────────────────────────────────────────────
assistant = client.beta.assistants.create(
    name="FitMate – Anytime Fitness Assistant",
    model="gpt-4o",
    instructions=prompt,
    tools=[{"type": "file_search"}],
    tool_resources={"file_search": {"vector_store_ids": [vs_id]}},
)
asst_id = assistant.id
print("✅  Assistant created:", asst_id)

# ───────────────────────────────────────────────────────────────────────────────
# 4.  Persist the IDs so the Streamlit app can load them
# ───────────────────────────────────────────────────────────────────────────────
ids_path = Path("ids")
ids_path.mkdir(exist_ok=True)

(ids_path / "vector_store_id.txt").write_text(vs_id)
(ids_path / "af_assistant_id.txt").write_text(asst_id)

print("💾  IDs written to 'ids/'")
print("\nAll done!  Start / reload the Streamlit app and test a query like:\n"
      "   What’s the phone number for Anytime Fitness Drummoyne?")

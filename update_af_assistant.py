# update_af_assistant.py

from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

# Replace with your uploaded file ID
file_id = "file-XctK3uJCZUJpRvkyJBs8hw"

# Load assistant ID
with open("af_assistant_id.txt", "r") as f:
    assistant_id = f.read().strip()

# Attach file to the assistant
updated = client.beta.assistants.update(
    assistant_id=assistant_id,
    tool_resources={"file_search": {"file_ids": [file_id]}}
)

print("✅ File attached to assistant.")

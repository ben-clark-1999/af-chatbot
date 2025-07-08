from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

# Step 1: Upload club directory file to existing vector store
vs_id = "vs_686b72b9b3ac81919b71dc0c7a5df5d7"  # ← your vector store ID

# Upload the new file and wait for indexing to complete
file_batch = client.beta.vector_stores.file_batches.upload_and_poll(
    vector_store_id=vs_id,
    files=[open("data/club_directory.txt", "rb")],
)
print("✅ Uploaded and indexed club_directory.txt to vector store.")

# Step 2: Load your assistant prompt
with open("data/af_prompt.txt") as f:
    prompt = f.read()

# Step 3: Create the assistant with file_search + vector store
assistant = client.beta.assistants.create(
    name="FitMate – Anytime Fitness Assistant",
    model="gpt-4o",
    instructions=prompt,
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vs_id]
        }
    },
)

# Step 4: Save assistant ID for reuse
print("✅ Assistant created:", assistant.id)
with open("ids/af_assistant_id.txt", "w") as f:
    f.write(assistant.id)

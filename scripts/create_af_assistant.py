from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

vs_id = "vs_686b72b9b3ac81919b71dc0c7a5df5d7"   # ← your vector-store ID

with open("data/af_prompt.txt") as f:
    prompt = f.read()

assistant = client.beta.assistants.create(       # 🔸 note the .beta.
    name        = "FitMate – Anytime Fitness Assistant",
    model       = "gpt-4o",
    instructions= prompt,
    tools=[{"type": "file_search"}],
    tool_resources={
        "file_search": {
            "vector_store_ids": [vs_id]
        }
    },
)

print("✅ Assistant created:", assistant.id)
with open("af_assistant_id.txt", "w") as f:
    f.write(assistant.id)

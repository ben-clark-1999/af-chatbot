# chat_af_responses.py
# Terminal chat with manual RAG (vector-store query → GPT-4o)

from openai import OpenAI
from dotenv import load_dotenv
import os, time, warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)  # silence old-API warnings
load_dotenv()
client = OpenAI()

# ⬅️  Put your vector-store ID here
VS_ID = "vs_686b72b9b3ac81919b71dc0c7a5df5d7"

# Load the FitMate system prompt
with open("data/af_prompt.txt") as f:
    SYSTEM_PROMPT = f.read().strip()

print("💬 Chatting with FitMate (RAG).  Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if not user_input:
        continue
    if user_input.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    # 1️⃣  Retrieve relevant FAQ chunks
    results = client.vector_stores.query(
        vector_store_id = VS_ID,
        query           = user_input,
        top_k           = 3
    )
    context = "\n---\n".join(doc.text for doc in results.data)

    # 2️⃣  Call GPT-4o with prompt + retrieved context
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"{SYSTEM_PROMPT}\n\n### Context (FAQ excerpts):\n{context}"
            },
            {"role": "user", "content": user_input}
        ]
    )
    answer = response.choices[0].message.content
    print("\nFitMate:", answer, "\n")

    # 3️⃣  Optional: append to log file
    with open("chat_log.txt", "a") as log:
        log.write(f"USER: {user_input}\n")
        log.write(f"FITMATE: {answer}\n\n")

from openai import OpenAI
from dotenv import load_dotenv
import os, time

load_dotenv()
client = OpenAI()

# Load your Assistant ID from file
with open("af_assistant_id.txt", "r") as f:
    ASSISTANT_ID = f.read().strip()

THREAD_FILE = "af_thread_id.txt"

# Reuse thread if it exists (to keep context)
if os.path.exists(THREAD_FILE):
    with open(THREAD_FILE, "r") as f:
        thread_id = f.read().strip()
else:
    thread = client.beta.threads.create()
    thread_id = thread.id
    with open(THREAD_FILE, "w") as f:
        f.write(thread_id)

print("💬 You are now chatting with FitMate. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ").strip()
    if not user_input:
        continue
    if user_input.lower() in {"exit", "quit"}:
        break


    if user_input.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    # Add user's message
    client.beta.threads.messages.create(
        thread_id=thread_id,
        role="user",
        content=user_input
    )

    # Start assistant run
    run = client.beta.threads.runs.create(
        thread_id=thread_id,
        assistant_id=ASSISTANT_ID
    )

    # Poll until done
    while run.status in {"queued", "in_progress"}:
        time.sleep(0.5)
        run = client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)

    # Get response
    messages = client.beta.threads.messages.list(thread_id=thread_id, order="asc")
    reply = messages.data[-1].content[0].text.value
    print("\nFitMate:", reply, "\n")

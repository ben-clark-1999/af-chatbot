from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()  # loads your OPENAI_API_KEY from .env if used

client = OpenAI()

with open("af_prompt.txt", "r") as f:
    prompt = f.read()

assistant = client.beta.assistants.create(
    name="FitMate – Anytime Fitness Assistant",
    model="gpt-4o-mini",  # or "gpt-4o"
    instructions=prompt
)

print("✅ Assistant created!")
print("Assistant ID:", assistant.id)

# Save to a text file for future reuse
with open("af_assistant_id.txt", "w") as f:
    f.write(assistant.id)

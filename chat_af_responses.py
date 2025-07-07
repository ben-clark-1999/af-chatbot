# chat_af_responses.py
from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

print("💬 Chatting with FitMate (Responses API). Type 'exit' to quit.\n")

chat_history = [
    {"role": "system", "content": "You are FitMate, the virtual assistant for Anytime Fitness Australia. Be helpful and respond based on the af_prompt.txt knowledge."}
]

while True:
    user_input = input("You: ").strip()
    if user_input.lower() in {"exit", "quit"}:
        print("👋 Goodbye!")
        break

    chat_history.append({"role": "user", "content": user_input})

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=chat_history,
    )

    answer = response.choices[0].message.content
    chat_history.append({"role": "assistant", "content": answer})
    print("\nFitMate:", answer, "\n")

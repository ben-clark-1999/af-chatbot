from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

# Upload the club_directory.txt file
with open("data/club_directory.txt", "rb") as f:
    file = client.files.create(file=f, purpose="assistants")

print("✅ Uploaded file ID:", file.id)

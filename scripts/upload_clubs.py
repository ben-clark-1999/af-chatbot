# scripts/upload_clubs.py
from openai import OpenAI
from dotenv import load_dotenv   # ← correct import
load_dotenv()

client = OpenAI()

file = client.files.create(
    file=open("data/club_directory.txt", "rb"),
    purpose="assistants"
)
print("✅ Uploaded File ID:", file.id)

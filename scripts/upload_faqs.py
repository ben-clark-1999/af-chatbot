from openai import OpenAI
from dotenv import load_dotenv
import os

load_dotenv()
client = OpenAI()

# Upload the FAQs file
file = client.files.create(
    file=open("af_faqs.txt", "rb"),
    purpose="assistants"
)

print("✅ Uploaded File ID:", file.id)

# check_vs_status.py
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

vs_id = "vs_686b72b9b3ac81919b71dc0c7a5df5d7"   # your store ID
status = client.vector_stores.retrieve(vs_id).status
print("Vector-store status:", status)
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI()

vs_id   = "vs_686b72b9b3ac81919b71dc0c7a5df5d7"     # your store
file_id = "file-XrHQiDZjP6jFJ7QeP8kt1B"                               # newest ID

client.vector_stores.file_batches.create(
    vector_store_id = vs_id,
    file_ids        = [file_id]
)

print("✅ New FAQ file queued for indexing.")

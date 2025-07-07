# build_vector_store.py
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
client = OpenAI()

file_id = "file-BWELpRUXBwsd7qCkAC9pfY"   # ← your real file ID

# 2-a  Create the vector store (note: NO .beta here)
vs = client.vector_stores.create(name="AF-FAQ-Store")
vs_id = vs.id
print("Vector store created:", vs_id)

# 2-b  Add the FAQ file into the store
client.vector_stores.file_batches.create(
    vector_store_id=vs_id,
    file_ids=[file_id]
)
print("File added to vector store.")

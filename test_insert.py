from supabase import create_client
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

response = supabase.table("Chat_logs").insert({
    "timestamp": datetime.now(timezone.utc).isoformat(),  # ✅ fixed here
    "user_input": "Test message",
    "bot_response": "This is a test"
}).execute()

print("✅ Inserted:", response)

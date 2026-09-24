import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Supabase error:", error)
    sys.exit(1)

# Test updating book_name of existing book #12
try:
    res = client.table("books").update({"book_name": "Gulfood 2026 Updated"}).eq("id", 12).execute()
    print("Updated book #12 book_name:", res.data)
    # Revert back
    client.table("books").update({"book_name": "Gulfood 2026"}).eq("id", 12).execute()
    print("Reverted book #12 successfully.")
except Exception as e:
    print("Update error:", e)

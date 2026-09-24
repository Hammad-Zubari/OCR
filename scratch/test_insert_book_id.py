import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Error:", error)
    sys.exit(1)

# Check what happens if we insert book_id column into books
try:
    res = client.table("books").insert({"book_id": "B_0127", "book_name": "China Import and Export"}).execute()
    print("Insert book_id into books result:", res.data)
except Exception as e:
    print("Insert book_id error:", e)

# Check what happens if we insert string book_id into exhibitor
try:
    res = client.table("exhibitor").insert({"book_id": "B_0127", "name": "Test Company"}).execute()
    print("Insert string book_id into exhibitor result:", res.data)
except Exception as e:
    print("Insert string book_id into exhibitor error:", e)

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Error:", error)
    sys.exit(1)

# Check all fields of a book
res = client.table("books").select("*").limit(1).execute()
print("Book fields:", res.data[0] if res.data else "No books")

# Check all fields of an exhibitor
res_ex = client.table("exhibitor").select("*").limit(1).execute()
print("Exhibitor fields:", res_ex.data[0] if res_ex.data else "No exhibitors")

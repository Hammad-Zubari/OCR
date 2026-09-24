import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Supabase error:", error)
    sys.exit(1)

# Try inserting a text book_id to see if table column is TEXT or INT
test_book_id = "B_TEST_001"
test_book_name = "Test Catalog Text ID"

try:
    res = client.table("books").insert({"id": test_book_id, "book_name": test_book_name}).execute()
    print("Inserted book with text ID successfully:", res.data)
    
    # Try inserting exhibitor with text book_id
    ex_res = client.table("exhibitor").insert({
        "name": "Test Company",
        "book_id": test_book_id
    }).execute()
    print("Inserted exhibitor with text book_id successfully:", ex_res.data)
    
    # Clean up test rows
    client.table("exhibitor").delete().eq("book_id", test_book_id).execute()
    client.table("books").delete().eq("id", test_book_id).execute()
    print("Cleaned up test data.")
except Exception as e:
    print("Error inserting text id:", e)

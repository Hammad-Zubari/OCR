import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Supabase error:", error)
else:
    books_res = client.table("books").select("id, book_name, uploaded_at").order("uploaded_at", desc=True).execute()
    books = books_res.data or []
    print(f"Found {len(books)} books:")
    target_table = "exhibitor"
    for b in books:
        c_res = client.table(target_table).select("id", count="exact").eq("book_id", b["id"]).limit(1).execute()
        count = c_res.count if c_res.count is not None else len(c_res.data or [])
        print(f"  Book #{b['id']} ({b['book_name']}): {count} records")



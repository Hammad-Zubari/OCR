import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Supabase connection error:", error)
    sys.exit(1)

print("Connected to Supabase.")

# Check books table
try:
    books_sample = client.table("books").select("*").limit(5).execute()
    print("Books sample rows:", books_sample.data)
except Exception as e:
    print("Error querying books:", e)

# Check exhibitor / exhibitors table
for tbl in ["exhibitor", "exhibitors"]:
    try:
        ex_sample = client.table(tbl).select("*").limit(3).execute()
        print(f"Table '{tbl}' sample rows:", ex_sample.data)
    except Exception as e:
        print(f"Error querying {tbl}:", e)

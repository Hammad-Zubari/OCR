import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import get_supabase_client

client, error = get_supabase_client()
if client:
    res = client.table("exhibitor").select("*").ilike("name", "%FAPAPO%").execute()
    data = res.data or []
    print("FAPAPO records found:", len(data))
    for r in data:
        print(r)

    res2 = client.table("exhibitor").select("*").eq("book_id", "B-0127").limit(10).execute()
    data2 = res2.data or []
    print(f"\nB-0127 records found: {len(data2)}")
    for r in data2:
        print(f"Name: {r.get('name')}, Address: '{r.get('address')}', Full: {r}")

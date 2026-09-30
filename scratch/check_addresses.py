import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import get_supabase_client

client, error = get_supabase_client()
if client:
    # 1. Fetch first 20 records
    res = client.table("exhibitor").select("*").limit(20).execute()
    data = res.data or []
    print(f"Total checked: {len(data)}")
    for i, row in enumerate(data[:10]):
        print(f"Row {i+1}: ID={row.get('id')}, Name={row.get('name')}, Address='{row.get('address')}', Keys={list(row.keys())}")

    # 2. Check if there are non-empty addresses in the DB
    res_addr = client.table("exhibitor").select("id, name, address, book_id").not_.is_("address", "null").neq("address", "").limit(5).execute()
    print("\nNon-empty address sample:")
    for r in res_addr.data or []:
        print(r)

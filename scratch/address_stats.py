import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import get_supabase_client

client, error = get_supabase_client()
if client:
    # Total exhibitors
    total_res = client.table("exhibitor").select("id", count="exact").execute()
    total = total_res.count

    # Non-empty address
    with_addr_res = client.table("exhibitor").select("id", count="exact").neq("address", "").not_.is_("address", "null").execute()
    with_addr = with_addr_res.count

    print(f"Total exhibitors in DB: {total}")
    print(f"Exhibitors WITH address in DB: {with_addr}")
    print(f"Exhibitors with EMPTY address in DB: {total - with_addr}")

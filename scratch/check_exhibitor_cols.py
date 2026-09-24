import sys, os
sys.path.insert(0, os.path.abspath('.'))
from app import get_supabase_client

client, error = get_supabase_client()
if client:
    res = client.table("exhibitor").select("*").limit(3).execute()
    data = res.data or []
    if data:
        print("Columns in exhibitor table:", list(data[0].keys()))
        print("Sample row:", data[0])
    else:
        print("No data in exhibitor table")

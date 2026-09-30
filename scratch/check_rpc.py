import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import get_supabase_client

client, error = get_supabase_client()
if error:
    print("Error:", error)
    sys.exit(1)

# Test if an exec_sql or sql rpc exists
try:
    res = client.rpc("exec_sql", {"sql": "SELECT 1"}).execute()
    print("RPC exec_sql exists:", res.data)
except Exception as e:
    print("No RPC exec_sql:", e)

import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app

client = app.app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 'admin-uuid-123'
    sess['role'] = 'admin'
    sess['user_name'] = 'Super Administrator'
    sess['email'] = 'admin@ecommercegateway.com'

res = client.get('/admin/exhibitors?page=1&limit=10')
data = res.get_json()
exs = data.get('exhibitors', [])
print("First 10 records returned by /admin/exhibitors:")
for i, ex in enumerate(exs):
    print(f"[{i+1}] Book #{ex.get('book_id')} | Name: {ex.get('name')} | Address: '{ex.get('address')}' | Tel: {ex.get('tel')} | Email: {ex.get('email')} | Web: {ex.get('website')} | Fax: {ex.get('fax')}")

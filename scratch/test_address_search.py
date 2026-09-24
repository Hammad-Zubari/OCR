import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app

client = app.app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 'admin-uuid-123'
    sess['role'] = 'admin'
    sess['user_name'] = 'Super Administrator'
    sess['email'] = 'admin@ecommercegateway.com'

# Search by address keyword
res = client.get('/admin/exhibitors?page=1&limit=5&search=Prague')
data = res.get_json()
exs = data.get('exhibitors', [])
print("Search 'Prague' returned:", len(exs))
for ex in exs:
    print(f"Name: {ex.get('name')} | Address: {ex.get('address')} | Book: {ex.get('book_id')}")

# Select Book 4
res2 = client.get('/admin/exhibitors?page=1&limit=5&book_id=4')
data2 = res2.get_json()
exs2 = data2.get('exhibitors', [])
print("\nBook 4 first 5 records:")
for ex in exs2:
    print(f"Name: {ex.get('name')} | Address: {ex.get('address')} | Book: {ex.get('book_id')}")

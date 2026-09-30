import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app

client = app.app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 'admin-uuid-123'
    sess['role'] = 'admin'
    sess['user_name'] = 'Super Administrator'
    sess['email'] = 'admin@ecommercegateway.com'

res = client.get('/admin/exhibitors?page=1&limit=5')
print('Status:', res.status_code)
if res.status_code == 200:
    data = res.get_json()
    exs = data.get('exhibitors', [])
    print(f"Total returned: {len(exs)}, Total in DB: {data.get('total')}")
    if exs:
        first = exs[0]
        print("Sample Exhibitor Record:")
        print(f"  Book ID: {first.get('book_id')}")
        print(f"  Name: {first.get('name')}")
        print(f"  Address: {first.get('address')}")
        print(f"  Tel: {first.get('tel')}")
        print(f"  Email: {first.get('email')}")
        print(f"  Website: {first.get('website')}")
        print(f"  Fax: {first.get('fax')}")

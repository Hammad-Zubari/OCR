import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app

client = app.app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 'admin-uuid-123'
    sess['role'] = 'admin'
    sess['user_name'] = 'Super Administrator'
    sess['email'] = 'admin@ecommercegateway.com'

res = client.get('/admin')
print('GET /admin status:', res.status_code)
html = res.get_data(as_text=True)
print('Length of rendered HTML:', len(html))
print('Contains Ecommerce Gateway:', 'Ecommerce Gateway' in html)
print('Contains Baseline System Offset:', 'Baseline System Offset' in html)
print('Contains 3,200.00 Credits:', '3,200.00 Credits' in html)
print('Contains Left Sidebar Navigation:', 'sidebar-nav' in html)
print('Contains Any Emoji?:', any(ord(c) > 127000 for c in html))

res2 = client.get('/ecom')
print('GET /ecom status:', res2.status_code)

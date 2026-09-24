import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app

client = app.app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 'admin-uuid-123'
    sess['role'] = 'admin'
    sess['user_name'] = 'Super Administrator'
    sess['email'] = 'admin@ecommercegateway.com'

endpoints = [
    ('/admin', 'GET', 200),
    ('/ecom', 'GET', 200),
    ('/admin/overview-metrics?timeframe=all', 'GET', 200),
    ('/admin/overview-metrics?timeframe=today', 'GET', 200),
    ('/admin/overview-metrics?timeframe=7d', 'GET', 200),
    ('/admin/overview-metrics?timeframe=30d', 'GET', 200),
    ('/admin/credit-ledger?timeframe=all', 'GET', 200),
    ('/admin/save-activities?timeframe=all', 'GET', 200),
    ('/admin/ledger-report-data?timeframe=all', 'GET', 200),
    ('/admin/users', 'GET', 200),
    ('/admin/books', 'GET', 200),
    ('/admin/exhibitors?page=1&limit=50', 'GET', 200),
    ('/admin/credit-ledger/export', 'GET', 200),
    ('/admin/save-activities/export', 'GET', 200),
    ('/admin/export-exhibitors', 'GET', 200)
]

all_passed = True
for url, method, expected in endpoints:
    if method == 'GET':
        r = client.get(url)
    status_match = (r.status_code == expected)
    if not status_match:
        all_passed = False
    print(f"[{'PASS' if status_match else 'FAIL'}] {method} {url} -> {r.status_code} (Expected {expected})")

if all_passed:
    print("\nALL 15 ADMIN ENDPOINTS PASSED PERFECTLY!")
else:
    print("\nSOME ENDPOINTS FAILED!")

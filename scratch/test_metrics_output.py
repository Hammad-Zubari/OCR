import sys, os
sys.path.insert(0, os.path.abspath('.'))
import app
client = app.app.test_client()

with client.session_transaction() as sess:
    sess['user_id'] = 'test-admin-id'
    sess['role'] = 'admin'
    sess['user_name'] = 'Super Admin'
    sess['email'] = 'admin@ecommercegateway.com'

res = client.get('/admin/overview-metrics?timeframe=all')
print('Status:', res.status_code)
if res.status_code == 200:
    data = res.get_json()
    metrics = data.get('metrics', {})
    print('Baseline Credits:', metrics.get('base_credits'))
    print('Live Credits:', metrics.get('live_credits_used'))
    print('Total Credits Used (3200 + Live):', metrics.get('total_credits_used'))
    print('Base Cost USD:', metrics.get('base_cost_usd'))
    print('Live Cost USD:', metrics.get('live_cost_usd'))
    print('Total Cost USD ($10 + Live):', metrics.get('total_cost_usd'))
    print('Parse Credits:', metrics.get('total_parse_credits'))
    print('Extract Credits:', metrics.get('total_extract_credits'))
    print('Total DB records:', metrics.get('total_exhibitors'))
    print('Total books:', metrics.get('total_books'))

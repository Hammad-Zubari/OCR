with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('def admin_export_exhibitors():')
print(text[start+800:start+2200])

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('def admin_export_exhibitors():')
print(text[start+1800:start+3000])

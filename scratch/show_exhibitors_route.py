with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

start = text.find('def admin_get_exhibitors():')
print(text[start:start+1800])

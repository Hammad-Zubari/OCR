with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

lines = text.splitlines()
for i, line in enumerate(lines):
    if 'admin.html' in line or 'def admin' in line or '/admin' in line:
        print(f"Line {i+1}: {line}")

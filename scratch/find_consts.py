with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines):
    if 'LANDING_CREDIT' in l or 'BASE_HISTORICAL' in l:
        print(f"Line {i+1}: {l.strip()}")

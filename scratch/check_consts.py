with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, l in enumerate(lines[:80]):
    if 'BASE_HISTORICAL' in l or 'LANDING_CREDIT' in l:
        print(f"Line {i+1}: {l.strip()}")

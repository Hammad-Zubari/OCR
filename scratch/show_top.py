with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(40, 70):
    print(f"{i+1}: {lines[i]}", end='')

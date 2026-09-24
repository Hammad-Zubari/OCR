with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i in range(2165, 2185):
    print(f"{i+1}: {lines[i]}", end='')

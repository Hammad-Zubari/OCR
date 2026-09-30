with open('templates/admin.html', 'r', encoding='utf-8') as f:
    text = f.read()

# Let us check the JS functions present in admin.html
import re
functions = re.findall(r'function\s+([a-zA-Z0-9_]+)\s*\(', text)
print("JS functions found in admin.html:", functions)

with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = '@app.route("/ecom")'
replacement = '@app.route("/admin")\n@app.route("/ecom")'

if '@app.route("/admin")\n@app.route("/ecom")' not in text:
    text = text.replace(target, replacement, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Added @app.route('/admin') alias!")
else:
    print("Alias already present")

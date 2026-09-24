with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

target = 'ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv"}'
replacement = '''ALLOWED_EXCEL_EXTENSIONS = {".xlsx", ".xls", ".csv"}

# LandingAI Credit System & Baseline Historical Offset
LANDING_CREDIT_RATE_USD = 0.035
BASE_HISTORICAL_CREDITS = 3200.0
BASE_HISTORICAL_COST_USD = 10.00'''

if target in text and 'LANDING_CREDIT_RATE_USD' not in text:
    text = text.replace(target, replacement, 1)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(text)
    print("Added constants at top of app.py!")
else:
    print("Target already replaced or not found")

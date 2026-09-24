with open('app.py', 'r', encoding='utf-8') as f:
    text = f.read()

# 1. Constants
if 'BASE_HISTORICAL_CREDITS' not in text:
    text = text.replace(
        'LANDING_CREDIT_RATE_USD = 0.035',
        'LANDING_CREDIT_RATE_USD = 0.035\nBASE_HISTORICAL_CREDITS = 3200.0\nBASE_HISTORICAL_COST_USD = 10.00'
    )

# 2. admin_overview_metrics calculations
old_m = '''        total_extractions = len(credit_entries)
        total_credits_used = sum(float(e.get("total_credits", 0.0)) for e in credit_entries)
        total_parse_credits = sum(float(e.get("parse_credits", 0.0)) for e in credit_entries)
        total_extract_credits = sum(float(e.get("extract_credits", 0.0)) for e in credit_entries)
        total_pages_processed = sum(int(e.get("pages_processed", 0)) for e in credit_entries)
        total_records_extracted = sum(int(e.get("records_extracted", 0)) for e in credit_entries)
        total_cost_usd = sum(float(e.get("cost_estimate_usd", 0.0)) for e in credit_entries)'''

new_m = '''        total_extractions = len(credit_entries)
        live_credits_used = sum(float(e.get("total_credits", 0.0)) for e in credit_entries)
        total_parse_credits = sum(float(e.get("parse_credits", 0.0)) for e in credit_entries)
        total_extract_credits = sum(float(e.get("extract_credits", 0.0)) for e in credit_entries)
        total_pages_processed = sum(int(e.get("pages_processed", 0)) for e in credit_entries)
        total_records_extracted = sum(int(e.get("records_extracted", 0)) for e in credit_entries)
        live_cost_usd = sum(float(e.get("cost_estimate_usd", 0.0)) for e in credit_entries)

        # Baseline offset: 3,200.00 credits and $10.00 USD
        base_credits = BASE_HISTORICAL_CREDITS if timeframe in ["all", "cumulative"] else 0.0
        base_cost_usd = BASE_HISTORICAL_COST_USD if timeframe in ["all", "cumulative"] else 0.0
        total_credits_used = base_credits + live_credits_used
        total_cost_usd = base_cost_usd + live_cost_usd'''

if old_m in text:
    text = text.replace(old_m, new_m)
    print("Replaced metrics calculation!")

# 3. Add base keys to json response
old_json_target = '"total_credits_used": round(total_credits_used, 2),'
new_json_target = '''"base_credits": BASE_HISTORICAL_CREDITS,
                "base_cost_usd": BASE_HISTORICAL_COST_USD,
                "live_credits_used": round(live_credits_used, 2),
                "live_cost_usd": round(live_cost_usd, 3),
                "total_credits_used": round(total_credits_used, 2),'''

if old_json_target in text and '"base_credits":' not in text:
    text = text.replace(old_json_target, new_json_target)
    print("Updated JSON return fields!")

# 4. Update admin_ledger_report_data
old_ledger_calc = '''        total_credits = sum(float(e.get("total_credits", 0.0)) for e in credit_entries)
        total_parse = sum(float(e.get("parse_credits", 0.0)) for e in credit_entries)
        total_extract = sum(float(e.get("extract_credits", 0.0)) for e in credit_entries)
        total_pages = sum(int(e.get("pages_processed", 0)) for e in credit_entries)
        total_records_extracted = sum(int(e.get("records_extracted", 0)) for e in credit_entries)
        total_cost_usd = sum(float(e.get("cost_estimate_usd", 0.0)) for e in credit_entries)'''

new_ledger_calc = '''        live_credits = sum(float(e.get("total_credits", 0.0)) for e in credit_entries)
        total_parse = sum(float(e.get("parse_credits", 0.0)) for e in credit_entries)
        total_extract = sum(float(e.get("extract_credits", 0.0)) for e in credit_entries)
        total_pages = sum(int(e.get("pages_processed", 0)) for e in credit_entries)
        total_records_extracted = sum(int(e.get("records_extracted", 0)) for e in credit_entries)
        live_cost_usd = sum(float(e.get("cost_estimate_usd", 0.0)) for e in credit_entries)

        base_credits = BASE_HISTORICAL_CREDITS if timeframe in ["all", "cumulative"] else 0.0
        base_cost = BASE_HISTORICAL_COST_USD if timeframe in ["all", "cumulative"] else 0.0
        total_credits = base_credits + live_credits
        total_cost_usd = base_cost + live_cost_usd'''

if old_ledger_calc in text:
    text = text.replace(old_ledger_calc, new_ledger_calc)
    print("Replaced ledger calculation!")

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(text)
print("app.py updated successfully!")

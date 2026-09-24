# -*- coding: utf-8 -*-
with open("templates/admin.html", "w", encoding="utf-8") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Ecommerce Gateway - Enterprise Admin Command Center & Credit Ledger</title>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --primary: #1e40af;
            --primary-dark: #1e3a8a;
            --primary-light: #eff6ff;
            --primary-accent: #2563eb;
            --sidebar-bg: #0f172a;
            --sidebar-hover: #1e293b;
            --sidebar-active: #2563eb;
            --sidebar-text: #94a3b8;
            --sidebar-text-active: #ffffff;
            --bg: #f8fafc;
            --card: #ffffff;
            --border: #e2e8f0;
            --border-dark: #cbd5e1;
            --text-main: #0f172a;
            --text-muted: #64748b;
            --success: #15803d;
            --success-bg: #f0fdf4;
            --warning: #b45309;
            --warning-bg: #fffbeb;
            --danger: #b91c1c;
            --danger-bg: #fef2f2;
            --purple: #6d28d9;
            --purple-bg: #f5f3ff;
            --cyan: #0e7490;
            --cyan-bg: #ecfeff;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: var(--bg);
            color: var(--text-main);
            min-height: 100vh;
            display: flex;
            flex-direction: column;
            -webkit-font-smoothing: antialiased;
        }

        .svg-icon {
            display: inline-block;
            width: 18px;
            height: 18px;
            stroke-width: 2;
            stroke: currentColor;
            fill: none;
            stroke-linecap: round;
            stroke-linejoin: round;
            vertical-align: middle;
            flex-shrink: 0;
        }
        .svg-icon.lg { width: 22px; height: 22px; }
        .svg-icon.xl { width: 26px; height: 26px; }
        .svg-icon.sm { width: 14px; height: 14px; }

        .top-header {
            background: #ffffff;
            border-bottom: 1px solid var(--border);
            padding: 12px 28px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            position: sticky;
            top: 0;
            z-index: 90;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
        }

        .header-brand-wrap { display: flex; align-items: center; gap: 14px; }

        .header-logo-badge {
            background: linear-gradient(135deg, #1e40af, #2563eb);
            color: #ffffff;
            font-weight: 800;
            font-size: 15px;
            padding: 8px 14px;
            border-radius: 8px;
            letter-spacing: 0.5px;
            display: flex;
            align-items: center;
            gap: 8px;
            box-shadow: 0 2px 4px rgba(37,99,235,0.2);
        }

        .header-title-group h1 { font-size: 16px; font-weight: 700; color: var(--text-main); line-height: 1.2; }
        .header-title-group p { font-size: 12px; color: var(--text-muted); }

        .header-actions-wrap { display: flex; align-items: center; gap: 12px; }

        .header-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            text-decoration: none;
            cursor: pointer;
            transition: all 0.15s ease;
            border: 1px solid transparent;
        }

        .header-btn-primary { background: var(--primary); color: #ffffff; }
        .header-btn-primary:hover { background: var(--primary-dark); }
        .header-btn-secondary { background: #ffffff; border-color: var(--border-dark); color: var(--text-main); }
        .header-btn-secondary:hover { background: var(--bg); border-color: #94a3b8; }
        .header-btn-logout { background: #fef2f2; color: #b91c1c; border-color: #fecaca; }
        .header-btn-logout:hover { background: #fee2e2; color: #991b1b; }

        .user-status-pill {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: #f1f5f9;
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 12px;
            font-weight: 500;
            color: var(--text-main);
        }

        .role-tag {
            background: #dbeafe;
            color: #1e40af;
            font-size: 10px;
            font-weight: 700;
            padding: 2px 6px;
            border-radius: 4px;
            text-transform: uppercase;
        }

        .app-layout { display: flex; flex: 1; min-height: calc(100vh - 61px); }

        .sidebar {
            width: 270px;
            background: var(--sidebar-bg);
            color: var(--sidebar-text);
            display: flex;
            flex-direction: column;
            border-right: 1px solid rgba(255,255,255,0.06);
            flex-shrink: 0;
        }

        .sidebar-section-title {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.8px;
            color: #64748b;
            padding: 20px 20px 8px;
        }

        .sidebar-menu {
            list-style: none;
            padding: 0 10px;
            display: flex;
            flex-direction: column;
            gap: 4px;
        }

        .sidebar-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 14px;
            border-radius: 8px;
            color: var(--sidebar-text);
            text-decoration: none;
            font-size: 13.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.15s ease;
        }

        .sidebar-item:hover { background: var(--sidebar-hover); color: #ffffff; }
        .sidebar-item.active { background: var(--sidebar-active); color: var(--sidebar-text-active); box-shadow: 0 2px 8px rgba(37,99,235,0.3); }

        .sidebar-badge {
            margin-left: auto;
            background: rgba(255,255,255,0.12);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            padding: 2px 7px;
            border-radius: 10px;
        }
        .sidebar-item.active .sidebar-badge { background: rgba(255,255,255,0.25); }

        .sidebar-footer {
            margin-top: auto;
            padding: 16px;
            border-top: 1px solid rgba(255,255,255,0.08);
            background: rgba(0,0,0,0.15);
        }

        .baseline-credit-card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px;
            padding: 12px;
            margin-bottom: 12px;
        }

        .baseline-credit-card-header {
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #94a3b8;
            margin-bottom: 4px;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .baseline-credit-card-value {
            font-family: 'JetBrains Mono', monospace;
            font-size: 14px;
            font-weight: 700;
            color: #38bdf8;
        }

        .baseline-credit-card-sub { font-size: 11px; color: #64748b; margin-top: 2px; }

        .main-content {
            flex: 1;
            padding: 24px 32px 48px;
            overflow-y: auto;
            max-width: calc(100vw - 270px);
        }

        .view-panel { display: none; }
        .view-panel.active { display: block; }

        .view-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 24px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .view-title-group h2 {
            font-size: 20px;
            font-weight: 700;
            color: var(--text-main);
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .view-title-group p { font-size: 13px; color: var(--text-muted); margin-top: 3px; }

        .timeframe-bar {
            display: inline-flex;
            background: #ffffff;
            border: 1px solid var(--border-dark);
            border-radius: 8px;
            padding: 3px;
            box-shadow: 0 1px 2px rgba(0,0,0,0.04);
        }

        .timeframe-btn {
            border: none;
            background: transparent;
            padding: 6px 14px;
            font-size: 12.5px;
            font-weight: 600;
            color: var(--text-muted);
            border-radius: 6px;
            cursor: pointer;
            transition: all 0.12s ease;
        }
        .timeframe-btn:hover { color: var(--text-main); background: #f1f5f9; }
        .timeframe-btn.active { background: var(--primary); color: #ffffff; box-shadow: 0 1px 3px rgba(30,64,175,0.25); }

        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
            margin-bottom: 24px;
        }

        .kpi-card {
            background: #ffffff;
            border: 1px solid var(--border);
            border-radius: 10px;
            padding: 18px 20px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            position: relative;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        .kpi-card::before { content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--primary); }
        .kpi-card.purple::before { background: var(--purple); }
        .kpi-card.emerald::before { background: var(--success); }
        .kpi-card.cyan::before { background: var(--cyan); }
        .kpi-card.amber::before { background: var(--warning); }

        .kpi-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
        .kpi-label { font-size: 11.5px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; color: var(--text-muted); }
        .kpi-icon-wrap { width: 32px; height: 32px; border-radius: 6px; display: flex; align-items: center; justify-content: center; background: var(--bg); color: var(--text-muted); }
        .kpi-value { font-family: 'JetBrains Mono', monospace; font-size: 22px; font-weight: 700; color: var(--text-main); line-height: 1.1; margin-bottom: 6px; }
        .kpi-subtext { font-size: 11.5px; color: var(--text-muted); line-height: 1.3; }

        .telemetry-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 24px; }

        .section-card { background: #ffffff; border: 1px solid var(--border); border-radius: 10px; padding: 20px 22px; box-shadow: 0 1px 3px rgba(0,0,0,0.03); }
        .section-card-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; padding-bottom: 12px; border-bottom: 1px solid var(--border); }
        .section-card-title { font-size: 14.5px; font-weight: 700; color: var(--text-main); display: flex; align-items: center; gap: 8px; }

        .telemetry-row { display: flex; align-items: center; justify-content: space-between; padding: 10px 0; border-bottom: 1px dashed var(--border); font-size: 13px; }
        .telemetry-row:last-child { border-bottom: none; padding-bottom: 0; }
        .telemetry-label { color: var(--text-muted); font-weight: 500; display: flex; align-items: center; gap: 6px; }
        .telemetry-val { font-family: 'JetBrains Mono', monospace; font-weight: 600; color: var(--text-main); }

        .progress-bar-wrap { background: #e2e8f0; border-radius: 6px; height: 8px; overflow: hidden; margin: 8px 0 16px; }
        .progress-bar-fill { height: 100%; background: linear-gradient(90deg, #2563eb, #38bdf8); border-radius: 6px; }

        .table-responsive { overflow-x: auto; border: 1px solid var(--border); border-radius: 8px; background: #ffffff; }
        .custom-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
        .custom-table th { background: #f8fafc; color: #475569; font-weight: 700; padding: 12px 16px; border-bottom: 1px solid var(--border); text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; white-space: nowrap; }
        .custom-table td { padding: 12px 16px; border-bottom: 1px solid var(--border); color: var(--text-main); vertical-align: middle; }
        .custom-table tr:last-child td { border-bottom: none; }
        .custom-table tr:hover td { background: #f8fafc; }

        .badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 4px; font-size: 11.5px; font-weight: 600; }
        .badge-success { background: var(--success-bg); color: var(--success); }
        .badge-warning { background: var(--warning-bg); color: var(--warning); }
        .badge-danger { background: var(--danger-bg); color: var(--danger); }
        .badge-primary { background: var(--primary-light); color: var(--primary); }
        .badge-purple { background: var(--purple-bg); color: var(--purple); }
        .mono { font-family: 'JetBrains Mono', monospace; }

        .btn { display: inline-flex; align-items: center; gap: 6px; padding: 7px 14px; border-radius: 6px; font-size: 12.5px; font-weight: 600; cursor: pointer; border: 1px solid transparent; transition: all 0.15s ease; text-decoration: none; }
        .btn-primary { background: var(--primary); color: #ffffff; }
        .btn-primary:hover { background: var(--primary-dark); }
        .btn-secondary { background: #ffffff; border-color: var(--border-dark); color: var(--text-main); }
        .btn-secondary:hover { background: #f1f5f9; border-color: #94a3b8; }
        .btn-success { background: #15803d; color: #ffffff; }
        .btn-success:hover { background: #166534; }
        .btn-danger { background: #b91c1c; color: #ffffff; }
        .btn-danger:hover { background: #991b1b; }
        .btn-sm { padding: 4px 10px; font-size: 11.5px; }

        .filter-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
        .search-input-wrap { position: relative; flex: 1; max-width: 380px; }
        .search-input-wrap input { width: 100%; padding: 8px 12px 8px 34px; border: 1px solid var(--border-dark); border-radius: 6px; font-size: 13px; background: #ffffff; outline: none; }
        .search-input-wrap input:focus { border-color: var(--primary-accent); box-shadow: 0 0 0 3px rgba(37,99,235,0.1); }
        .search-input-wrap .search-icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: #94a3b8; pointer-events: none; }

        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15,23,42,0.65); backdrop-filter: blur(3px); display: none; align-items: center; justify-content: center; z-index: 200; padding: 20px; }
        .modal-overlay.active { display: flex; }
        .modal-card { background: #ffffff; border-radius: 12px; max-width: 850px; width: 100%; max-height: 90vh; display: flex; flex-direction: column; box-shadow: 0 20px 25px -5px rgba(0,0,0,0.2); overflow: hidden; }
        .modal-header { padding: 16px 24px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; background: #f8fafc; }
        .modal-body { padding: 24px; overflow-y: auto; }
        .modal-footer { padding: 14px 24px; border-top: 1px solid var(--border); background: #f8fafc; display: flex; align-items: center; justify-content: flex-end; gap: 10px; }

        .form-group { margin-bottom: 16px; }
        .form-label { display: block; font-size: 12.5px; font-weight: 600; color: var(--text-main); margin-bottom: 6px; }
        .form-input, .form-select { width: 100%; padding: 8px 12px; border: 1px solid var(--border-dark); border-radius: 6px; font-size: 13px; outline: none; }
        .form-input:focus, .form-select:focus { border-color: var(--primary-accent); }

        .footer { background: #ffffff; border-top: 1px solid var(--border); padding: 14px 28px; font-size: 12px; color: var(--text-muted); display: flex; align-items: center; justify-content: space-between; margin-top: auto; }

        @media print {
            .top-header, .sidebar, .footer, .timeframe-bar, .filter-toolbar, .no-print, .btn, .search-input-wrap { display: none !important; }
            body, .app-layout, .main-content { background: #ffffff !important; color: #000000 !important; padding: 0 !important; margin: 0 !important; max-width: 100% !important; }
            .modal-overlay { position: static !important; background: transparent !important; display: block !important; padding: 0 !important; }
            .modal-card { max-width: 100% !important; box-shadow: none !important; border: none !important; }
            .print-statement-sheet { padding: 20px !important; border: 1px solid #000000 !important; }
        }
    </style>
</head>
<body>
""")
print("Part 1 written successfully!")

# -*- coding: utf-8 -*-
with open("templates/admin.html", "a", encoding="utf-8") as f:
    f.write("""
    <!-- Top Executive Header -->
    <header class="top-header">
        <div class="header-brand-wrap">
            <div class="header-logo-badge">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/></svg>
                <span>Ecommerce Gateway</span>
            </div>
            <div class="header-title-group">
                <h1>Enterprise Admin Command Center</h1>
                <p>OCR Ingestion, LandingAI Credit Accounting & Master Exhibitor Repository</p>
            </div>
        </div>

        <div class="header-actions-wrap">
            <button class="header-btn header-btn-primary" onclick="openPrintLedgerModal()">
                <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                <span>Print Executive Ledger</span>
            </button>
            <a href="/ecom" class="header-btn header-btn-secondary">
                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>
                <span>Extractor App</span>
            </a>
            <div class="user-status-pill">
                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/></svg>
                <span id="headerUserEmail">{{ session.get('user_name') or session.get('email', 'Admin User') }}</span>
                <span class="role-tag">{{ session.get('role', 'Admin') }}</span>
            </div>
            <a href="/logout" class="header-btn header-btn-logout">
                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
                <span>Logout</span>
            </a>
        </div>
    </header>

    <!-- App Body Layout -->
    <div class="app-layout">

        <!-- Left Sidebar Navigation -->
        <aside class="sidebar" id="sidebar-nav">
            <div class="sidebar-section-title">Navigation Menu</div>
            <ul class="sidebar-menu">
                <li>
                    <a class="sidebar-item active" onclick="switchTab('overviewTab')">
                        <svg class="svg-icon" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                        <span>Executive Overview</span>
                    </a>
                </li>
                <li>
                    <a class="sidebar-item" onclick="switchTab('creditLedgerTab')">
                        <svg class="svg-icon" viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                        <span>LandingAI Credit Ledger</span>
                        <span class="sidebar-badge mono" id="sidebarCreditBadge">3,200 cr</span>
                    </a>
                </li>
                <li>
                    <a class="sidebar-item" onclick="switchTab('saveActivitiesTab')">
                        <svg class="svg-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                        <span>User Ingestion Audit</span>
                        <span class="sidebar-badge mono" id="sidebarSavesBadge">0</span>
                    </a>
                </li>
                <li>
                    <a class="sidebar-item" onclick="switchTab('usersTab')">
                        <svg class="svg-icon" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                        <span>Users & Access Control</span>
                        <span class="sidebar-badge" id="sidebarPendingBadge" style="display:none; background:#b91c1c;">0</span>
                    </a>
                </li>
                <li>
                    <a class="sidebar-item" onclick="switchTab('booksTab')">
                        <svg class="svg-icon" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                        <span>Catalog Books & DB</span>
                    </a>
                </li>
                <li>
                    <a class="sidebar-item" onclick="switchTab('exhibitorsTab')">
                        <svg class="svg-icon" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                        <span>Exhibitor Master Records</span>
                    </a>
                </li>
            </ul>

            <div class="sidebar-footer">
                <div class="baseline-credit-card">
                    <div class="baseline-credit-card-header">
                        <span>Baseline System Offset</span>
                        <svg class="svg-icon sm" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                    </div>
                    <div class="baseline-credit-card-value">3,200.00 Credits</div>
                    <div class="baseline-credit-card-sub">Base Cost: $10.000 USD</div>
                </div>

                <div style="font-size: 11px; color: #64748b; display: flex; align-items: center; gap: 6px;">
                    <span style="width: 8px; height: 8px; border-radius: 50%; background: #22c55e; display: inline-block;"></span>
                    <span>Supabase Cloud: Active</span>
                </div>
            </div>
        </aside>

        <!-- Main Content Area -->
        <main class="main-content">

            <!-- VIEW 1: EXECUTIVE OVERVIEW -->
            <div id="overviewTab" class="view-panel active">
                <div class="view-header">
                    <div class="view-title-group">
                        <h2>
                            <svg class="svg-icon lg" viewBox="0 0 24 24"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
                            Executive Command Center & Operational Metrics
                        </h2>
                        <p>Real-time analytics of LandingAI credit burn rate, user data ingestion, and cloud database capacity.</p>
                    </div>

                    <!-- Timeframe Filter -->
                    <div class="timeframe-bar">
                        <button class="timeframe-btn" data-timeframe="today" onclick="setTimeframe('today')">Today (Daily)</button>
                        <button class="timeframe-btn" data-timeframe="7d" onclick="setTimeframe('7d')">Last 7 Days (Weekly)</button>
                        <button class="timeframe-btn" data-timeframe="30d" onclick="setTimeframe('30d')">This Month (Monthly)</button>
                        <button class="timeframe-btn active" data-timeframe="all" onclick="setTimeframe('all')">All-Time Cumulative</button>
                    </div>
                </div>

                <!-- 4 Main KPI Cards -->
                <div class="kpi-grid">
                    <div class="kpi-card purple">
                        <div class="kpi-card-header">
                            <span class="kpi-label">LandingAI Credits Used</span>
                            <div class="kpi-icon-wrap">
                                <svg class="svg-icon" viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                            </div>
                        </div>
                        <div class="kpi-value" id="kpiTotalCredits">3,200.00</div>
                        <div class="kpi-subtext" id="kpiCreditsBreakdown">Base: 3,200.00 | Live: 0.00 (Parse: 0.00 | Extract: 0.00)</div>
                    </div>

                    <div class="kpi-card emerald">
                        <div class="kpi-card-header">
                            <span class="kpi-label">Estimated API Expenditure</span>
                            <div class="kpi-icon-wrap">
                                <svg class="svg-icon" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                            </div>
                        </div>
                        <div class="kpi-value" id="kpiTotalCost">$ 10.000</div>
                        <div class="kpi-subtext" id="kpiCostBreakdown">Base: $10.000 | Live: $0.000 USD</div>
                    </div>

                    <div class="kpi-card cyan">
                        <div class="kpi-card-header">
                            <span class="kpi-label">Total Database Records</span>
                            <div class="kpi-icon-wrap">
                                <svg class="svg-icon" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                            </div>
                        </div>
                        <div class="kpi-value" id="kpiTotalExhibitors">6,475</div>
                        <div class="kpi-subtext" id="kpiDbStorage">Est. Storage: 4.85 MB | 4 Books</div>
                    </div>

                    <div class="kpi-card amber">
                        <div class="kpi-card-header">
                            <span class="kpi-label">Users & Authorization</span>
                            <div class="kpi-icon-wrap">
                                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            </div>
                        </div>
                        <div class="kpi-value" id="kpiTotalUsers">2</div>
                        <div class="kpi-subtext" id="kpiUsersBreakdown">2 Approved | 0 Pending</div>
                    </div>
                </div>

                <!-- Executive Telemetry: Consumption Breakdown & Storage Monitor -->
                <div class="telemetry-grid">
                    <!-- Telemetry Card 1: LandingAI Engine Allocation -->
                    <div class="section-card">
                        <div class="section-card-header">
                            <span class="section-card-title">
                                <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
                                LandingAI ADE Consumption Breakdown
                            </span>
                            <span class="badge badge-purple mono" id="adeUnitRate">$0.035 / Credit</span>
                        </div>

                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 14 14"/></svg>
                                Historical Baseline Credits
                            </span>
                            <span class="telemetry-val" id="telemetryBaseCredits">3,200.00 cr</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                                Historical Baseline Cost
                            </span>
                            <span class="telemetry-val" id="telemetryBaseCost">$10.000 USD</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
                                Live Parse Credits (Layout & OCR)
                            </span>
                            <span class="telemetry-val" id="telemetryParseCredits">0.00 cr</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"/><line x1="3" y1="9" x2="21" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>
                                Live Extract Credits (Schema Extraction)
                            </span>
                            <span class="telemetry-val" id="telemetryExtractCredits">0.00 cr</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/></svg>
                                Total Processed PDF Pages
                            </span>
                            <span class="telemetry-val" id="telemetryPagesProcessed">0 pages</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>
                                Total Raw Records Extracted
                            </span>
                            <span class="telemetry-val" id="telemetryRecordsExtracted">0 records</span>
                        </div>
                    </div>

                    <!-- Telemetry Card 2: Cloud Database & Storage Diagnostics -->
                    <div class="section-card">
                        <div class="section-card-header">
                            <span class="section-card-title">
                                <svg class="svg-icon" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                                Cloud Database & Repository Diagnostics
                            </span>
                            <span class="badge badge-success">Online & Synced</span>
                        </div>

                        <div>
                            <div style="display:flex; justify-content:space-between; font-size:12px; margin-bottom:4px;">
                                <span style="color:var(--text-muted);">Estimated Table Storage Volume</span>
                                <span class="mono" style="font-weight:700;" id="storageBarLabel">4.85 MB</span>
                            </div>
                            <div class="progress-bar-wrap">
                                <div class="progress-bar-fill" id="storageProgressBar" style="width: 24%;"></div>
                            </div>
                        </div>

                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10"/></svg>
                                Total Master Exhibitor Rows
                            </span>
                            <span class="telemetry-val" id="telemetryTotalExhibitors">6,475 rows</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/></svg>
                                Registered Catalog Editions
                            </span>
                            <span class="telemetry-val" id="telemetryTotalBooks">4 editions</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/></svg>
                                Ingested by System Users
                            </span>
                            <span class="telemetry-val" id="telemetrySavedByUsers">0 rows saved</span>
                        </div>
                        <div class="telemetry-row">
                            <span class="telemetry-label">
                                <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                                Access Protection Status
                            </span>
                            <span class="badge badge-success">Admin Policy Active</span>
                        </div>
                    </div>
                </div>

                <!-- Live Activity Stream: Recent Extractions & Saves -->
                <div class="telemetry-grid">
                    <div class="section-card">
                        <div class="section-card-header">
                            <span class="section-card-title">
                                <svg class="svg-icon" viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                                Recent LandingAI Extractions
                            </span>
                            <a class="btn btn-secondary btn-sm" onclick="switchTab('creditLedgerTab')">View Full Ledger</a>
                        </div>
                        <div id="overviewRecentExtractionsTable">
                            <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;">Loading extractions ledger...</div>
                        </div>
                    </div>

                    <div class="section-card">
                        <div class="section-card-header">
                            <span class="section-card-title">
                                <svg class="svg-icon" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                                Recent Database Saves
                            </span>
                            <a class="btn btn-secondary btn-sm" onclick="switchTab('saveActivitiesTab')">View Full Audit</a>
                        </div>
                        <div id="overviewRecentSavesTable">
                            <div style="padding: 24px; text-align: center; color: var(--text-muted); font-size: 13px;">Loading save activities...</div>
                        </div>
                    </div>
                </div>

                <!-- User Productivity Roster -->
                <div class="section-card" style="margin-top: 20px;">
                    <div class="section-card-header">
                        <span class="section-card-title">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            User Workload, Uploads & Credit Expenditure Roster
                        </span>
                        <a href="/admin/save-activities/export" class="btn btn-success btn-sm">
                            <svg class="svg-icon sm" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Export Roster (Excel)
                        </a>
                    </div>
                    <div class="table-responsive">
                        <table class="custom-table" id="overviewUserProductivityTable">
                            <thead>
                                <tr>
                                    <th>#</th>
                                    <th>User Email</th>
                                    <th>Role</th>
                                    <th>Access Status</th>
                                    <th>PDF Uploads / Extractions</th>
                                    <th>Pages Converted</th>
                                    <th>ADE Credits Used</th>
                                    <th>Records Extracted</th>
                                    <th>Saved To DB</th>
                                    <th>Est. Cost ($)</th>
                                </tr>
                            </thead>
                            <tbody>
                                <tr><td colspan="10" style="text-align:center; padding:24px; color:var(--text-muted);">Loading user productivity data...</td></tr>
                            </tbody>
                        </table>
                    </div>
                </div>

                <!-- Executive Quick Actions -->
                <div class="section-card" style="margin-top: 20px;">
                    <div class="section-card-header">
                        <span class="section-card-title">
                            <svg class="svg-icon" viewBox="0 0 24 24"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                            Executive Quick Actions & Report Printing
                        </span>
                    </div>
                    <div style="display: flex; gap: 12px; flex-wrap: wrap;">
                        <button class="btn btn-success" onclick="openPrintLedgerModal()">
                            <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                            Print Executive Audit & Credit Ledger Report
                        </button>
                        <a href="/admin/credit-ledger/export" class="btn btn-secondary">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Download Credit Ledger (Excel)
                        </a>
                        <a href="/admin/save-activities/export" class="btn btn-secondary">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Download User Ingestion Log (Excel)
                        </a>
                        <a href="/admin/export-exhibitors" class="btn btn-secondary">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Download Full Database (Excel)
                        </a>
                        <button class="btn btn-primary" onclick="switchTab('usersTab')">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M16 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="8.5" cy="7" r="4"/><line x1="20" y1="8" x2="20" y2="14"/><line x1="23" y1="11" x2="17" y2="11"/></svg>
                            Review Pending User Approvals
                        </button>
                    </div>
                </div>
            </div>
""")
print("Part 2 written successfully!")

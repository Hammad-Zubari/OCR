# -*- coding: utf-8 -*-
with open("templates/admin.html", "a", encoding="utf-8") as f:
    f.write("""
            <!-- VIEW 2: LANDINGAI CREDIT LEDGER -->
            <div id="creditLedgerTab" class="view-panel">
                <div class="view-header">
                    <div class="view-title-group">
                        <h2>
                            <svg class="svg-icon lg" viewBox="0 0 24 24"><rect x="1" y="4" width="22" height="16" rx="2" ry="2"/><line x1="1" y1="10" x2="23" y2="10"/></svg>
                            LandingAI Credit Expenditure Ledger
                        </h2>
                        <p>Itemized log of every document extraction, ADE API credit burn, and duration.</p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <a href="/admin/credit-ledger/export" class="btn btn-success">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Export to Excel (.xlsx)
                        </a>
                        <button class="btn btn-danger" onclick="clearAllCreditLedger()">
                            <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            Clear Ledger
                        </button>
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="custom-table" id="creditLedgerTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Timestamp</th>
                                <th>User Email</th>
                                <th>Document / File Name</th>
                                <th>Pages</th>
                                <th>Parse Credits</th>
                                <th>Extract Credits</th>
                                <th>Total Credits</th>
                                <th>Est. Cost ($)</th>
                                <th>Duration</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="11" style="text-align:center; padding:32px; color:var(--text-muted);">Loading credit ledger transactions...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- VIEW 3: USER INGESTION AUDIT -->
            <div id="saveActivitiesTab" class="view-panel">
                <div class="view-header">
                    <div class="view-title-group">
                        <h2>
                            <svg class="svg-icon lg" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="12" y1="18" x2="12" y2="12"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
                            User Database Ingestion Audit Log
                        </h2>
                        <p>Complete historical log of records saved into the Supabase database by operators.</p>
                    </div>
                    <div style="display: flex; gap: 10px;">
                        <a href="/admin/save-activities/export" class="btn btn-success">
                            <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                            Export to Excel (.xlsx)
                        </a>
                        <button class="btn btn-danger" onclick="clearAllActivities()">
                            <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
                            Clear Activity Log
                        </button>
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="custom-table" id="saveActivitiesTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Timestamp</th>
                                <th>User Email</th>
                                <th>Catalog Book Target</th>
                                <th>Records Ingested</th>
                                <th>Extraction Session ID</th>
                                <th>Status</th>
                                <th>Action</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">Loading database save activities...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- VIEW 4: USERS & ACCESS CONTROL -->
            <div id="usersTab" class="view-panel">
                <div class="view-header">
                    <div class="view-title-group">
                        <h2>
                            <svg class="svg-icon lg" viewBox="0 0 24 24"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                            User Accounts & Access Authorization
                        </h2>
                        <p>Approve operator accounts, grant Admin privileges, or revoke system access.</p>
                    </div>
                </div>

                <div class="filter-toolbar">
                    <div class="search-input-wrap">
                        <svg class="svg-icon sm search-icon" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        <input type="text" id="userSearchInput" placeholder="Search users by email or role..." oninput="filterUsersTable()">
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="custom-table" id="usersTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>User Email</th>
                                <th>Role</th>
                                <th>Account Status</th>
                                <th>Registered Date</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">Loading user roster...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- VIEW 5: CATALOG BOOKS & DB -->
            <div id="booksTab" class="view-panel">
                <div class="view-header">
                    <div class="view-title-group">
                        <h2>
                            <svg class="svg-icon lg" viewBox="0 0 24 24"><path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/><path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/></svg>
                            Catalog Editions & Book Directories
                        </h2>
                        <p>Manage registered exhibition books, year editions, and mapped exhibitor volumes.</p>
                    </div>
                </div>

                <div class="filter-toolbar">
                    <div class="search-input-wrap">
                        <svg class="svg-icon sm search-icon" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        <input type="text" id="bookSearchInput" placeholder="Search catalog books..." oninput="filterBooksTable()">
                    </div>
                </div>

                <div class="table-responsive">
                    <table class="custom-table" id="booksTable">
                        <thead>
                            <tr>
                                <th>Book ID</th>
                                <th>Catalog Book Title</th>
                                <th>Year</th>
                                <th>Exhibitor Count</th>
                                <th>Publisher / Notes</th>
                                <th>Actions</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">Loading catalog books...</td></tr>
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- VIEW 6: EXHIBITOR MASTER RECORDS -->
            <div id="exhibitorsTab" class="view-panel">
                <div class="view-header">
                    <div class="view-title-group">
                        <h2>
                            <svg class="svg-icon lg" viewBox="0 0 24 24"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>
                            Exhibitor Master Database Browser
                        </h2>
                        <p>Search, inspect, and export all 6,475+ exhibitor records stored across all catalogs.</p>
                    </div>
                    <a href="/admin/export-exhibitors" class="btn btn-success">
                        <svg class="svg-icon" viewBox="0 0 24 24"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                        Export Master Database (Excel)
                    </a>
                </div>

                <div class="filter-toolbar">
                    <div class="search-input-wrap">
                        <svg class="svg-icon sm search-icon" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        <input type="text" id="exhibitorSearchInput" placeholder="Search by company, email, country, stall...">
                    </div>
                    <select id="exhibitorBookFilter" class="form-select" style="max-width:240px;" onchange="loadExhibitors(1)">
                        <option value="">All Catalog Books</option>
                    </select>
                    <button class="btn btn-secondary" onclick="loadExhibitors(1)">
                        <svg class="svg-icon sm" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                        Search
                    </button>
                </div>

                <div class="table-responsive">
                    <table class="custom-table" id="exhibitorsTable">
                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Company Name</th>
                                <th>Email</th>
                                <th>Phone</th>
                                <th>Website</th>
                                <th>Country</th>
                                <th>Stall / Hall</th>
                                <th>Book ID</th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">Loading exhibitor database records...</td></tr>
                        </tbody>
                    </table>
                </div>

                <div style="display:flex; justify-content:space-between; align-items:center; margin-top:16px;">
                    <span style="font-size:12.5px; color:var(--text-muted);" id="exhibitorsPaginationInfo">Showing page 1</span>
                    <div style="display:flex; gap:8px;">
                        <button class="btn btn-secondary btn-sm" id="btnPrevPage" onclick="changeExhibitorPage(-1)" disabled>Previous</button>
                        <button class="btn btn-secondary btn-sm" id="btnNextPage" onclick="changeExhibitorPage(1)">Next</button>
                    </div>
                </div>
            </div>

        </main>
    </div>

    <!-- Executive Footer -->
    <footer class="footer">
        <div>
            <strong>Ecommerce Gateway</strong> - Enterprise Document Intelligence & LandingAI Credit Ledger System
        </div>
        <div>
            (c) 2026 Ecommerce Gateway. All rights reserved. | Cloud Connection: <span class="badge badge-success">Online</span>
        </div>
    </footer>
""")
print("Part 3 written successfully!")

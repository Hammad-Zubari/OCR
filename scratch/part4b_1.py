# -*- coding: utf-8 -*-
with open("templates/admin.html", "a", encoding="utf-8") as f:
    f.write("""
    <!-- JAVASCRIPT CONTROLLER -->
    <script>
        let currentPeriod = 'all';
        let currentExhibitorPage = 1;
        let totalExhibitorPages = 1;

        document.addEventListener('DOMContentLoaded', () => {
            loadOverviewMetrics();
        });

        function switchTab(tabId) {
            document.querySelectorAll('.view-panel').forEach(panel => {
                panel.classList.remove('active');
            });
            document.querySelectorAll('.sidebar-item').forEach(item => {
                item.classList.remove('active');
            });

            const targetPanel = document.getElementById(tabId);
            if (targetPanel) {
                targetPanel.classList.add('active');
            }

            document.querySelectorAll('.sidebar-item').forEach(item => {
                if (item.getAttribute('onclick') && item.getAttribute('onclick').includes(tabId)) {
                    item.classList.add('active');
                }
            });

            if (tabId === 'overviewTab') loadOverviewMetrics();
            if (tabId === 'creditLedgerTab') loadCreditLedger();
            if (tabId === 'saveActivitiesTab') loadSaveActivities();
            if (tabId === 'usersTab') loadUsers();
            if (tabId === 'booksTab') loadBooks();
            if (tabId === 'exhibitorsTab') loadExhibitors(1);
        }

        function setTimeframe(period) {
            currentPeriod = period;
            document.querySelectorAll('.timeframe-btn').forEach(btn => {
                btn.classList.toggle('active', btn.getAttribute('data-timeframe') === period);
            });
            loadOverviewMetrics();
        }

        async function loadOverviewMetrics() {
            try {
                const res = await fetch(`/admin/overview-metrics?timeframe=${currentPeriod}`);
                const json = await res.json();
                if (!json.success) return;

                const m = json.metrics;

                const baseCredits = m.base_credits || 3200.0;
                const liveCredits = m.live_credits_used || 0.0;
                const totalCredits = m.total_credits_used || (baseCredits + liveCredits);
                document.getElementById('kpiTotalCredits').innerText = Number(totalCredits).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('kpiCreditsBreakdown').innerText = `Base: ${baseCredits.toLocaleString()} | Live: ${liveCredits.toFixed(2)} (Parse: ${(m.total_parse_credits||0).toFixed(2)} | Extract: ${(m.total_extract_credits||0).toFixed(2)})`;
                document.getElementById('sidebarCreditBadge').innerText = `${Math.round(totalCredits).toLocaleString()} cr`;

                const baseCost = m.base_cost_usd || 10.00;
                const liveCost = m.live_cost_usd || 0.00;
                const totalCost = m.total_cost_usd || (baseCost + liveCost);
                document.getElementById('kpiTotalCost').innerText = `$ ${Number(totalCost).toFixed(3)}`;
                document.getElementById('kpiCostBreakdown').innerText = `Base: $${baseCost.toFixed(3)} | Live: $${liveCost.toFixed(3)} USD`;

                document.getElementById('kpiTotalExhibitors').innerText = (m.total_exhibitors || 0).toLocaleString();
                document.getElementById('kpiDbStorage').innerText = `Est. Storage: ${m.est_storage_mb || 0} MB | ${m.total_books || 0} Books`;

                document.getElementById('kpiTotalUsers').innerText = m.total_users || 0;
                document.getElementById('kpiUsersBreakdown').innerText = `${m.approved_users || 0} Approved | ${m.pending_users || 0} Pending`;
                
                if (m.pending_users > 0) {
                    const pb = document.getElementById('sidebarPendingBadge');
                    pb.innerText = m.pending_users;
                    pb.style.display = 'inline-block';
                }

                document.getElementById('telemetryBaseCredits').innerText = `${baseCredits.toLocaleString()} cr`;
                document.getElementById('telemetryBaseCost').innerText = `$${baseCost.toFixed(3)} USD`;
                document.getElementById('telemetryParseCredits').innerText = `${(m.total_parse_credits || 0).toFixed(2)} cr`;
                document.getElementById('telemetryExtractCredits').innerText = `${(m.total_extract_credits || 0).toFixed(2)} cr`;
                document.getElementById('telemetryPagesProcessed').innerText = `${m.total_pages_processed || 0} pages`;
                document.getElementById('telemetryRecordsExtracted').innerText = `${m.total_records_extracted || 0} records`;

                document.getElementById('telemetryTotalExhibitors').innerText = `${(m.total_exhibitors || 0).toLocaleString()} rows`;
                document.getElementById('telemetryTotalBooks').innerText = `${m.total_books || 0} editions`;
                document.getElementById('telemetrySavedByUsers').innerText = `${m.total_records_saved_by_users || 0} rows saved`;
                document.getElementById('sidebarSavesBadge').innerText = m.total_records_saved_by_users || 0;
                document.getElementById('storageBarLabel').innerText = `${m.est_storage_mb || 0} MB (${m.total_exhibitors || 0} rows)`;

                renderUserProductivity(m.user_productivity || []);
                renderOverviewRecentExtractions(m.recent_extractions || []);
                renderOverviewRecentSaves(m.recent_activities || []);

            } catch (err) {
                console.error('[Error loading overview metrics]', err);
            }
        }

        function renderUserProductivity(users) {
            const tbody = document.querySelector('#overviewUserProductivityTable tbody');
            if (!users || users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="10" style="text-align:center; padding:24px; color:var(--text-muted);">No user activity recorded in this period.</td></tr>';
                return;
            }

            let html = '';
            users.forEach((u, i) => {
                const roleBadge = u.role === 'admin' 
                    ? '<span class="badge badge-purple">Admin</span>'
                    : '<span class="badge badge-primary">Operator</span>';
                
                const statusBadge = u.approved 
                    ? '<span class="badge badge-success">Approved</span>' 
                    : '<span class="badge badge-danger">Pending</span>';

                html += `
                    <tr>
                        <td class="mono">${i + 1}</td>
                        <td style="font-weight:600;">${escapeHtml(u.email)}</td>
                        <td>${roleBadge}</td>
                        <td>${statusBadge}</td>
                        <td class="mono">${u.extractions_count || 0}</td>
                        <td class="mono">${u.pages_processed || 0}</td>
                        <td class="mono" style="color:var(--purple); font-weight:700;">${(u.credits_used || 0).toFixed(2)} cr</td>
                        <td class="mono">${u.records_extracted || 0}</td>
                        <td class="mono" style="color:var(--success); font-weight:700;">${u.records_saved || 0} saved</td>
                        <td class="mono" style="font-weight:700;">$${(u.estimated_cost_usd || 0).toFixed(3)}</td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }

        function renderOverviewRecentExtractions(entries) {
            const container = document.getElementById('overviewRecentExtractionsTable');
            if (!entries || entries.length === 0) {
                container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-muted); font-size:12.5px;">No extractions logged yet.</div>';
                return;
            }

            let html = '<div class="table-responsive"><table class="custom-table"><thead><tr><th>File Name</th><th>User</th><th>Pages</th><th>Credits</th><th>Cost</th></tr></thead><tbody>';
            entries.forEach(e => {
                html += `
                    <tr>
                        <td style="font-weight:600; max-width:180px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(e.file_name || e.document_name || 'Document')}">
                            ${escapeHtml(e.file_name || e.document_name || 'Document')}
                        </td>
                        <td style="font-size:11.5px; color:var(--text-muted);">${escapeHtml((e.user_email || 'anonymous').split('@')[0])}</td>
                        <td class="mono">${e.pages_processed || 1}</td>
                        <td class="mono" style="font-weight:700; color:var(--purple);">${Number(e.total_credits || 0).toFixed(2)}</td>
                        <td class="mono" style="font-weight:600;">$${Number(e.cost_estimate_usd || 0).toFixed(3)}</td>
                    </tr>
                `;
            });
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }

        function renderOverviewRecentSaves(saves) {
            const container = document.getElementById('overviewRecentSavesTable');
            if (!saves || saves.length === 0) {
                container.innerHTML = '<div style="padding:20px; text-align:center; color:var(--text-muted); font-size:12.5px;">No saves logged yet.</div>';
                return;
            }

            let html = '<div class="table-responsive"><table class="custom-table"><thead><tr><th>User</th><th>Catalog Target</th><th>Saved Rows</th><th>Timestamp</th></tr></thead><tbody>';
            saves.forEach(s => {
                html += `
                    <tr>
                        <td style="font-weight:600; font-size:11.5px;">${escapeHtml(s.user_email || 'anonymous')}</td>
                        <td style="font-size:12px; color:var(--text-muted);">${escapeHtml(s.book_name || 'Exhibitors')}</td>
                        <td class="mono" style="font-weight:700; color:var(--success);">+${s.saved_count || 0}</td>
                        <td style="font-size:11px; color:var(--text-muted);">${s.created_at_formatted || s.created_at || '-'}</td>
                    </tr>
                `;
            });
            html += '</tbody></table></div>';
            container.innerHTML = html;
        }
""")
print("Part 4b_1 written!")

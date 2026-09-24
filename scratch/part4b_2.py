# -*- coding: utf-8 -*-
with open("templates/admin.html", "a", encoding="utf-8") as f:
    f.write("""
        // LOAD CREDIT LEDGER
        async function loadCreditLedger() {
            const tbody = document.querySelector('#creditLedgerTable tbody');
            tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding:32px; color:var(--text-muted);">Loading credit ledger transactions...</td></tr>';
            try {
                const res = await fetch('/admin/credit-ledger?timeframe=all');
                const json = await res.json();
                const entries = json.entries || [];
                if (entries.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding:32px; color:var(--text-muted);">No credit transactions recorded.</td></tr>';
                    return;
                }

                let html = '';
                entries.forEach((e, i) => {
                    html += `
                        <tr>
                            <td class="mono">${i + 1}</td>
                            <td style="font-size:12px; color:var(--text-muted);">${e.created_at_formatted || e.created_at}</td>
                            <td style="font-weight:600;">${escapeHtml(e.user_email || 'anonymous')}</td>
                            <td style="font-weight:600; max-width:200px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;" title="${escapeHtml(e.file_name || e.document_name || 'Document')}">
                                ${escapeHtml(e.file_name || e.document_name || 'Document')}
                            </td>
                            <td class="mono">${e.pages_processed || 1}</td>
                            <td class="mono">${Number(e.parse_credits || 0).toFixed(2)}</td>
                            <td class="mono">${Number(e.extract_credits || 0).toFixed(2)}</td>
                            <td class="mono" style="font-weight:700; color:var(--purple);">${Number(e.total_credits || 0).toFixed(2)} cr</td>
                            <td class="mono" style="font-weight:700; color:var(--success);">$${Number(e.cost_estimate_usd || 0).toFixed(3)}</td>
                            <td class="mono" style="font-size:11.5px;">${e.duration_seconds || 0}s</td>
                            <td>
                                <button class="btn btn-danger btn-sm" onclick="deleteCreditLedgerEntry('${e.id}')">Delete</button>
                            </td>
                        </tr>
                    `;
                });
                tbody.innerHTML = html;
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="11" style="text-align:center; padding:32px; color:var(--danger);">Error loading credit ledger.</td></tr>';
            }
        }

        async function deleteCreditLedgerEntry(id) {
            if (!confirm('Are you sure you want to delete this credit entry?')) return;
            try {
                const res = await fetch(`/admin/credit-ledger/${id}`, { method: 'DELETE' });
                const json = await res.json();
                if (json.success) loadCreditLedger();
                else alert(json.error || 'Failed to delete entry');
            } catch (e) { alert('Error deleting entry'); }
        }

        async function clearAllCreditLedger() {
            if (!confirm('WARNING: Are you sure you want to wipe the credit ledger? Historical baseline (3,200 cr / $10) will remain intact.')) return;
            try {
                const res = await fetch('/admin/credit-ledger/clear', { method: 'POST' });
                const json = await res.json();
                if (json.success) {
                    loadCreditLedger();
                    loadOverviewMetrics();
                } else {
                    alert(json.error || 'Failed to clear ledger');
                }
            } catch (e) { alert('Error clearing ledger'); }
        }

        // LOAD SAVE ACTIVITIES
        async function loadSaveActivities() {
            const tbody = document.querySelector('#saveActivitiesTable tbody');
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">Loading database save activities...</td></tr>';
            try {
                const res = await fetch('/admin/save-activities?timeframe=all');
                const json = await res.json();
                const activities = json.activities || [];
                if (activities.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">No database save activities recorded.</td></tr>';
                    return;
                }

                let html = '';
                activities.forEach((a, i) => {
                    html += `
                        <tr>
                            <td class="mono">${i + 1}</td>
                            <td style="font-size:12px; color:var(--text-muted);">${a.created_at_formatted || a.created_at}</td>
                            <td style="font-weight:600;">${escapeHtml(a.user_email || 'anonymous')}</td>
                            <td style="font-weight:600;">${escapeHtml(a.book_name || a.book_id || 'Exhibitors Master')}</td>
                            <td class="mono" style="font-weight:700; color:var(--success);">+${a.saved_count || 0} rows</td>
                            <td class="mono" style="font-size:11px; color:var(--text-muted);">${escapeHtml(a.extraction_id || '-')}</td>
                            <td><span class="badge badge-success">Saved Successfully</span></td>
                            <td>
                                <button class="btn btn-danger btn-sm" onclick="deleteSaveActivity('${a.id}')">Delete</button>
                            </td>
                        </tr>
                    `;
                });
                tbody.innerHTML = html;
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--danger);">Error loading save activities.</td></tr>';
            }
        }

        async function deleteSaveActivity(id) {
            if (!confirm('Are you sure you want to delete this activity entry?')) return;
            try {
                const res = await fetch(`/admin/save-activities/${id}`, { method: 'DELETE' });
                const json = await res.json();
                if (json.success) loadSaveActivities();
                else alert(json.error || 'Failed to delete activity');
            } catch (e) { alert('Error deleting activity'); }
        }

        async function clearAllActivities() {
            if (!confirm('WARNING: Are you sure you want to clear all user save activities?')) return;
            try {
                const res = await fetch('/admin/save-activities/clear', { method: 'POST' });
                const json = await res.json();
                if (json.success) {
                    loadSaveActivities();
                    loadOverviewMetrics();
                } else {
                    alert(json.error || 'Failed to clear activities');
                }
            } catch (e) { alert('Error clearing activities'); }
        }

        // USERS & ACCESS CONTROL
        let allUsersData = [];
        async function loadUsers() {
            const tbody = document.querySelector('#usersTable tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">Loading user accounts...</td></tr>';
            try {
                const res = await fetch('/admin/users');
                const json = await res.json();
                allUsersData = json.users || [];
                renderUsersTable(allUsersData);
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--danger);">Error loading users roster.</td></tr>';
            }
        }

        function renderUsersTable(users) {
            const tbody = document.querySelector('#usersTable tbody');
            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">No users found.</td></tr>';
                return;
            }

            let html = '';
            users.forEach((u, i) => {
                const roleBadge = u.role === 'admin'
                    ? '<span class="badge badge-purple">Admin</span>'
                    : '<span class="badge badge-primary">User</span>';

                const statusBadge = u.approved
                    ? '<span class="badge badge-success">Approved</span>'
                    : '<span class="badge badge-danger">Pending Approval</span>';

                const approveBtn = !u.approved
                    ? `<button class="btn btn-success btn-sm" onclick="approveUser('${u.id}')">Approve</button>`
                    : `<button class="btn btn-secondary btn-sm" onclick="toggleUserStatus('${u.id}', false)">Revoke Access</button>`;

                const toggleRoleBtn = u.role === 'admin'
                    ? `<button class="btn btn-secondary btn-sm" onclick="toggleUserRole('${u.id}', 'user')">Set as User</button>`
                    : `<button class="btn btn-secondary btn-sm" onclick="toggleUserRole('${u.id}', 'admin')">Promote Admin</button>`;

                html += `
                    <tr>
                        <td class="mono">${i + 1}</td>
                        <td style="font-weight:600;">${escapeHtml(u.email)}</td>
                        <td>${roleBadge}</td>
                        <td>${statusBadge}</td>
                        <td style="font-size:12px; color:var(--text-muted);">${u.created_at ? new Date(u.created_at).toLocaleDateString() : '-'}</td>
                        <td style="display:flex; gap:6px; flex-wrap:wrap;">
                            ${approveBtn}
                            ${toggleRoleBtn}
                            <button class="btn btn-danger btn-sm" onclick="deleteUser('${u.id}')">Delete</button>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }

        function filterUsersTable() {
            const query = document.getElementById('userSearchInput').value.toLowerCase();
            const filtered = allUsersData.filter(u => 
                (u.email || '').toLowerCase().includes(query) ||
                (u.role || '').toLowerCase().includes(query)
            );
            renderUsersTable(filtered);
        }

        async function approveUser(id) {
            try {
                const res = await fetch(`/admin/users/${id}/approve`, { method: 'POST' });
                const json = await res.json();
                if (json.success) loadUsers();
                else alert(json.error || 'Failed to approve user');
            } catch (e) { alert('Error approving user'); }
        }

        async function toggleUserStatus(id, approved) {
            try {
                const res = await fetch(`/admin/users/${id}/status`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ approved })
                });
                const json = await res.json();
                if (json.success) loadUsers();
                else alert(json.error || 'Failed to update user status');
            } catch (e) { alert('Error updating status'); }
        }

        async function toggleUserRole(id, role) {
            try {
                const res = await fetch(`/admin/users/${id}/role`, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({ role })
                });
                const json = await res.json();
                if (json.success) loadUsers();
                else alert(json.error || 'Failed to update user role');
            } catch (e) { alert('Error updating role'); }
        }

        async function deleteUser(id) {
            if (!confirm('Are you sure you want to delete this user account?')) return;
            try {
                const res = await fetch(`/admin/users/${id}`, { method: 'DELETE' });
                const json = await res.json();
                if (json.success) loadUsers();
                else alert(json.error || 'Failed to delete user');
            } catch (e) { alert('Error deleting user'); }
        }
""")
print("Part 4b_2 written!")

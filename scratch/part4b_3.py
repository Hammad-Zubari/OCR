# -*- coding: utf-8 -*-
with open("templates/admin.html", "a", encoding="utf-8") as f:
    f.write("""
        // BOOKS & DIRECTORIES
        let allBooksData = [];
        async function loadBooks() {
            const tbody = document.querySelector('#booksTable tbody');
            tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">Loading catalog books...</td></tr>';
            try {
                const res = await fetch('/admin/books');
                const json = await res.json();
                allBooksData = json.books || [];
                renderBooksTable(allBooksData);

                const bookFilter = document.getElementById('exhibitorBookFilter');
                bookFilter.innerHTML = '<option value="">All Catalog Books</option>';
                allBooksData.forEach(b => {
                    bookFilter.innerHTML += `<option value="${b.id}">${escapeHtml(b.book_name || b.name || `Book #${b.id}`)}</option>`;
                });
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--danger);">Error loading books.</td></tr>';
            }
        }

        function renderBooksTable(books) {
            const tbody = document.querySelector('#booksTable tbody');
            if (books.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align:center; padding:32px; color:var(--text-muted);">No catalog books registered.</td></tr>';
                return;
            }

            let html = '';
            books.forEach(b => {
                html += `
                    <tr>
                        <td class="mono">#${b.id}</td>
                        <td style="font-weight:700;">${escapeHtml(b.book_name || b.name || 'Catalog Book')}</td>
                        <td class="mono">${b.year || '-'}</td>
                        <td class="mono" style="font-weight:700; color:var(--primary);">${(b.exhibitor_count || 0).toLocaleString()} rows</td>
                        <td style="font-size:12px; color:var(--text-muted); max-width:240px;">${escapeHtml(b.publisher || b.description || '-')}</td>
                        <td style="display:flex; gap:6px;">
                            <button class="btn btn-secondary btn-sm" onclick="viewBookExhibitors('${b.id}')">View Records</button>
                            <button class="btn btn-secondary btn-sm" onclick="openEditBookModal('${b.id}', '${escapeHtml(b.book_name || b.name || '')}', '${escapeHtml(b.year || '')}', '${escapeHtml(b.publisher || b.description || '')}')">Edit</button>
                        </td>
                    </tr>
                `;
            });
            tbody.innerHTML = html;
        }

        function filterBooksTable() {
            const query = document.getElementById('bookSearchInput').value.toLowerCase();
            const filtered = allBooksData.filter(b => 
                (b.book_name || b.name || '').toLowerCase().includes(query) ||
                (b.publisher || '').toLowerCase().includes(query) ||
                String(b.year || '').includes(query)
            );
            renderBooksTable(filtered);
        }

        function viewBookExhibitors(bookId) {
            switchTab('exhibitorsTab');
            document.getElementById('exhibitorBookFilter').value = bookId;
            loadExhibitors(1);
        }

        function openEditBookModal(id, name, year, notes) {
            document.getElementById('editBookId').value = id;
            document.getElementById('editBookName').value = name;
            document.getElementById('editBookYear').value = year;
            document.getElementById('editBookNotes').value = notes;
            document.getElementById('editBookModal').classList.add('active');
        }

        function closeEditBookModal() {
            document.getElementById('editBookModal').classList.remove('active');
        }

        async function handleEditBookSubmit(e) {
            e.preventDefault();
            const id = document.getElementById('editBookId').value;
            const payload = {
                name: document.getElementById('editBookName').value,
                year: document.getElementById('editBookYear').value,
                publisher: document.getElementById('editBookNotes').value
            };

            try {
                const res = await fetch(`/admin/books/${id}`, {
                    method: 'PUT',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(payload)
                });
                const json = await res.json();
                if (json.success) {
                    closeEditBookModal();
                    loadBooks();
                } else {
                    alert(json.error || 'Failed to update book');
                }
            } catch (err) { alert('Error updating book'); }
        }

        // EXHIBITOR RECORDS
        async function loadExhibitors(page = 1) {
            currentExhibitorPage = page;
            const tbody = document.querySelector('#exhibitorsTable tbody');
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">Loading exhibitor database records...</td></tr>';

            const query = document.getElementById('exhibitorSearchInput').value.trim();
            const bookId = document.getElementById('exhibitorBookFilter').value;

            try {
                const res = await fetch(`/admin/exhibitors?page=${page}&limit=50&search=${encodeURIComponent(query)}&book_id=${encodeURIComponent(bookId)}`);
                const json = await res.json();
                const exhibitors = json.exhibitors || [];
                const total = json.total || exhibitors.length;
                totalExhibitorPages = Math.ceil(total / 50) || 1;

                document.getElementById('exhibitorsPaginationInfo').innerText = `Showing page ${page} of ${totalExhibitorPages} (${total.toLocaleString()} total records)`;
                document.getElementById('btnPrevPage').disabled = page <= 1;
                document.getElementById('btnNextPage').disabled = page >= totalExhibitorPages;

                if (exhibitors.length === 0) {
                    tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--text-muted);">No exhibitors found matching filter.</td></tr>';
                    return;
                }

                let html = '';
                exhibitors.forEach((ex, i) => {
                    html += `
                        <tr>
                            <td class="mono">${(page - 1) * 50 + i + 1}</td>
                            <td style="font-weight:700;">${escapeHtml(ex.company_name || ex.name || 'Exhibitor')}</td>
                            <td style="font-size:12px;">${escapeHtml(ex.email || '-')}</td>
                            <td class="mono" style="font-size:12px;">${escapeHtml(ex.phone || ex.contact_number || '-')}</td>
                            <td style="font-size:12px;"><a href="${escapeHtml(ex.website || '#')}" target="_blank" style="color:var(--primary);">${escapeHtml(ex.website || '-')}</a></td>
                            <td>${escapeHtml(ex.country || '-')}</td>
                            <td class="mono" style="font-weight:600;">${escapeHtml(ex.stall_no || ex.hall_no || '-')}</td>
                            <td class="mono">#${ex.book_id || '-'}</td>
                        </tr>
                    `;
                });
                tbody.innerHTML = html;
            } catch (err) {
                tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:32px; color:var(--danger);">Error loading exhibitors.</td></tr>';
            }
        }

        function changeExhibitorPage(delta) {
            const next = currentExhibitorPage + delta;
            if (next >= 1 && next <= totalExhibitorPages) {
                loadExhibitors(next);
            }
        }

        // PRINTABLE EXECUTIVE STATEMENT
        async function openPrintLedgerModal() {
            document.getElementById('printLedgerModal').classList.add('active');
            const body = document.getElementById('printStatementBody');
            body.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-muted);">Generating consolidated financial & operational ledger...</div>';

            try {
                const res = await fetch(`/admin/ledger-report-data?timeframe=${currentPeriod}`);
                const json = await res.json();
                if (!json.success) {
                    body.innerHTML = '<div style="color:var(--danger); text-align:center; padding:30px;">Error generating report.</div>';
                    return;
                }

                const s = json.summary || {};
                const users = json.user_summaries || [];
                const txs = json.transactions || [];

                const baseCredits = 3200.0;
                const baseCost = 10.00;
                const liveCredits = s.total_credits_used || 0.0;
                const liveCost = s.total_cost_usd || 0.0;
                const cumCredits = baseCredits + liveCredits;
                const cumCost = baseCost + liveCost;

                let html = `
                    <div style="border: 2px solid #0f172a; border-radius: 8px; padding: 24px; font-family: 'Plus Jakarta Sans', sans-serif;">
                        <div style="display:flex; justify-content:space-between; align-items:flex-start; border-bottom: 2px solid #0f172a; padding-bottom: 16px; margin-bottom: 20px;">
                            <div>
                                <h1 style="font-size: 22px; font-weight: 800; color: #0f172a; margin: 0; text-transform: uppercase; letter-spacing: 0.5px;">Ecommerce Gateway</h1>
                                <p style="font-size: 13px; color: #475569; margin-top: 3px; font-weight: 600;">Enterprise Document Intelligence & LandingAI Credit Accounting Ledger</p>
                                <p style="font-size: 11px; color: #64748b; margin-top: 2px;">Statement Period: <strong>${escapeHtml(json.timeframe_label || 'All-Time Cumulative')}</strong> | Report Generated: ${new Date().toLocaleString()}</p>
                            </div>
                            <div style="text-align:right;">
                                <div style="background: #0f172a; color: #ffffff; font-size: 11px; font-weight: 700; padding: 4px 10px; border-radius: 4px; display: inline-block;">EXECUTIVE AUDIT</div>
                                <p style="font-size: 11px; color: #64748b; margin-top: 4px;">Ref: EG-OCR-AUDIT-${Date.now().toString().slice(-6)}</p>
                            </div>
                        </div>

                        <div style="display:grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px;">
                            <div style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; background: #f8fafc;">
                                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total Credits Used</div>
                                <div style="font-size: 18px; font-weight: 800; color: #0f172a; font-family: 'JetBrains Mono', monospace; margin: 4px 0;">${cumCredits.toLocaleString('en-US', {minimumFractionDigits:2})}</div>
                                <div style="font-size: 10px; color: #64748b;">Base: 3,200 | Live: ${liveCredits.toFixed(2)}</div>
                            </div>
                            <div style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; background: #f8fafc;">
                                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">Total Cost ($ USD)</div>
                                <div style="font-size: 18px; font-weight: 800; color: #0f172a; font-family: 'JetBrains Mono', monospace; margin: 4px 0;">$ ${cumCost.toFixed(3)}</div>
                                <div style="font-size: 10px; color: #64748b;">Base: $10.00 | Live: $${liveCost.toFixed(3)}</div>
                            </div>
                            <div style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; background: #f8fafc;">
                                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">Database Volume</div>
                                <div style="font-size: 18px; font-weight: 800; color: #0f172a; font-family: 'JetBrains Mono', monospace; margin: 4px 0;">${(s.total_exhibitors_in_db || 6475).toLocaleString()}</div>
                                <div style="font-size: 10px; color: #64748b;">${s.total_books_in_db || 4} Catalog Editions</div>
                            </div>
                            <div style="border: 1px solid #cbd5e1; border-radius: 6px; padding: 12px; background: #f8fafc;">
                                <div style="font-size: 10px; font-weight: 700; color: #64748b; text-transform: uppercase;">Pages Converted</div>
                                <div style="font-size: 18px; font-weight: 800; color: #0f172a; font-family: 'JetBrains Mono', monospace; margin: 4px 0;">${s.total_pages_processed || 0}</div>
                                <div style="font-size: 10px; color: #64748b;">Parse: ${(s.total_parse_credits||0).toFixed(1)} | Extract: ${(s.total_extract_credits||0).toFixed(1)}</div>
                            </div>
                        </div>

                        <h4 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 8px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px;">1. User Workload & Ingestion Audit</h4>
                        <table style="width:100%; border-collapse:collapse; font-size:12px; margin-bottom: 20px;">
                            <thead>
                                <tr style="background:#f1f5f9; border-bottom:1px solid #cbd5e1; text-align:left;">
                                    <th style="padding:8px;">User Email</th>
                                    <th style="padding:8px;">Extractions</th>
                                    <th style="padding:8px;">Pages</th>
                                    <th style="padding:8px;">ADE Credits</th>
                                    <th style="padding:8px;">Records Extracted</th>
                                    <th style="padding:8px;">Saved To DB</th>
                                    <th style="padding:8px;">Est. Cost ($)</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                if (users.length === 0) {
                    html += `<tr><td colspan="7" style="padding:12px; text-align:center; color:#64748b;">No individual operator activity recorded in this period.</td></tr>`;
                } else {
                    users.forEach(u => {
                        html += `
                            <tr style="border-bottom: 1px solid #e2e8f0;">
                                <td style="padding:8px; font-weight:600;">${escapeHtml(u.email)}</td>
                                <td style="padding:8px; font-family:monospace;">${u.extractions_count || 0}</td>
                                <td style="padding:8px; font-family:monospace;">${u.pages_processed || 0}</td>
                                <td style="padding:8px; font-family:monospace; font-weight:700;">${Number(u.credits_used || 0).toFixed(2)} cr</td>
                                <td style="padding:8px; font-family:monospace;">${u.records_extracted || 0}</td>
                                <td style="padding:8px; font-family:monospace; font-weight:700;">${u.records_saved || 0}</td>
                                <td style="padding:8px; font-family:monospace; font-weight:700;">$${Number(u.estimated_cost_usd || 0).toFixed(3)}</td>
                            </tr>
                        `;
                    });
                }

                html += `
                            </tbody>
                        </table>

                        <h4 style="font-size: 13px; font-weight: 700; text-transform: uppercase; color: #0f172a; margin-bottom: 8px; border-bottom: 1px solid #cbd5e1; padding-bottom: 4px;">2. Itemized Document Extraction Ledger</h4>
                        <table style="width:100%; border-collapse:collapse; font-size:11.5px; margin-bottom: 24px;">
                            <thead>
                                <tr style="background:#f1f5f9; border-bottom:1px solid #cbd5e1; text-align:left;">
                                    <th style="padding:6px 8px;">Date / Time</th>
                                    <th style="padding:6px 8px;">User</th>
                                    <th style="padding:6px 8px;">Document File</th>
                                    <th style="padding:6px 8px;">Pages</th>
                                    <th style="padding:6px 8px;">Credits</th>
                                    <th style="padding:6px 8px;">Cost ($)</th>
                                </tr>
                            </thead>
                            <tbody>
                `;

                if (txs.length === 0) {
                    html += `<tr><td colspan="6" style="padding:12px; text-align:center; color:#64748b;">No itemized transactions logged. Baseline historical credits: 3,200.00 ($10.000 USD).</td></tr>`;
                } else {
                    txs.slice(0, 25).forEach(t => {
                        html += `
                            <tr style="border-bottom: 1px solid #e2e8f0;">
                                <td style="padding:6px 8px; color:#64748b;">${t.created_at_formatted || t.created_at}</td>
                                <td style="padding:6px 8px; font-weight:600;">${escapeHtml((t.user_email||'').split('@')[0])}</td>
                                <td style="padding:6px 8px;">${escapeHtml(t.file_name || t.document_name || 'Document')}</td>
                                <td style="padding:6px 8px; font-family:monospace;">${t.pages_processed || 1}</td>
                                <td style="padding:6px 8px; font-family:monospace; font-weight:700;">${Number(t.total_credits || 0).toFixed(2)}</td>
                                <td style="padding:6px 8px; font-family:monospace;">$${Number(t.cost_estimate_usd || 0).toFixed(3)}</td>
                            </tr>
                        `;
                    });
                }

                html += `
                            </tbody>
                        </table>

                        <div style="display:flex; justify-content:space-between; margin-top:30px; padding-top:20px; border-top:1px dashed #cbd5e1;">
                            <div style="width:200px; text-align:center;">
                                <div style="border-bottom: 1px solid #0f172a; height: 35px; margin-bottom: 6px;"></div>
                                <span style="font-size:11px; font-weight:700; color:#475569; text-transform:uppercase;">System Operator</span>
                            </div>
                            <div style="width:200px; text-align:center;">
                                <div style="border-bottom: 1px solid #0f172a; height: 35px; margin-bottom: 6px;"></div>
                                <span style="font-size:11px; font-weight:700; color:#475569; text-transform:uppercase;">Auditor / Admin</span>
                            </div>
                            <div style="width:200px; text-align:center;">
                                <div style="border-bottom: 1px solid #0f172a; height: 35px; margin-bottom: 6px;"></div>
                                <span style="font-size:11px; font-weight:700; color:#475569; text-transform:uppercase;">Executive Sign-off</span>
                            </div>
                        </div>
                    </div>
                `;

                body.innerHTML = html;

            } catch (err) {
                body.innerHTML = '<div style="color:var(--danger); text-align:center; padding:30px;">Failed to generate statement.</div>';
            }
        }

        function closePrintLedgerModal() {
            document.getElementById('printLedgerModal').classList.remove('active');
        }

        function escapeHtml(str) {
            if (!str) return '';
            return String(str)
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
                .replace(/"/g, '&quot;')
                .replace(/'/g, '&#039;');
        }
    </script>
</body>
</html>
""")
print("Part 4b_3 written and templates/admin.html completed!")

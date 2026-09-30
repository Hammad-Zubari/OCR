# -*- coding: utf-8 -*-
with open('templates/admin.html', 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Update HTML Table Header
old_thead = """                        <thead>
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
                        </thead>"""

new_thead = """                        <thead>
                            <tr>
                                <th>#</th>
                                <th>Book ID</th>
                                <th>Company / Name</th>
                                <th>Address</th>
                                <th>Tel / Phone</th>
                                <th>Email</th>
                                <th>Website</th>
                                <th>Fax</th>
                            </tr>
                        </thead>"""

if old_thead in html:
    html = html.replace(old_thead, new_thead)
    print("Replaced Table Header!")

# 2. Update JS Renderer in loadExhibitors
old_js_loop = """                let html = '';
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
                });"""

new_js_loop = """                let html = '';
                exhibitors.forEach((ex, i) => {
                    const bookId = ex.book_id || '-';
                    const name = ex.name || ex.company_name || '-';
                    const address = ex.address || '-';
                    const tel = ex.tel || ex.tell || ex.phone || ex.contact_number || '-';
                    const email = ex.email || '-';
                    const website = ex.website || '-';
                    const fax = ex.fax || '-';

                    const emailCell = email !== '-' 
                        ? `<a href="mailto:${escapeHtml(email)}" style="color:var(--primary);">${escapeHtml(email)}</a>`
                        : '<span style="color:#94a3b8;">-</span>';

                    const websiteCell = website !== '-'
                        ? `<a href="${escapeHtml(website.startsWith('http') ? website : 'http://' + website)}" target="_blank" style="color:var(--primary); text-decoration:underline;">${escapeHtml(website)}</a>`
                        : '<span style="color:#94a3b8;">-</span>';

                    html += `
                        <tr>
                            <td class="mono">${(page - 1) * 50 + i + 1}</td>
                            <td class="mono" style="font-weight:700; color:var(--primary);">#${escapeHtml(bookId)}</td>
                            <td style="font-weight:700; max-width:220px;">${escapeHtml(name)}</td>
                            <td style="font-size:12px; color:var(--text-muted); max-width:260px;">${escapeHtml(address)}</td>
                            <td class="mono" style="font-size:12px;">${escapeHtml(tel)}</td>
                            <td style="font-size:12px;">${emailCell}</td>
                            <td style="font-size:12px;">${websiteCell}</td>
                            <td class="mono" style="font-size:12px; color:var(--text-muted);">${escapeHtml(fax)}</td>
                        </tr>
                    `;
                });"""

if old_js_loop in html:
    html = html.replace(old_js_loop, new_js_loop)
    print("Replaced JS loadExhibitors loop!")

with open('templates/admin.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Updated templates/admin.html successfully!")

# 3. Update app.py to include fax in search filters if missing
with open('app.py', 'r', encoding='utf-8') as f:
    app_code = f.read()

if 'f"tel.ilike.%{search}%"' in app_code and 'f"fax.ilike.%{search}%"' not in app_code:
    app_code = app_code.replace(
        'f"tel.ilike.%{search}%"',
        'f"tel.ilike.%{search}%",\n                    f"fax.ilike.%{search}%"'
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(app_code)
    print("Added fax filter in app.py search!")
else:
    print("fax filter already present in app.py or not needed.")

# -*- coding: utf-8 -*-
with open("templates/admin.html", "a", encoding="utf-8") as f:
    f.write("""
    <!-- PRINTABLE EXECUTIVE AUDIT & CREDIT LEDGER MODAL -->
    <div class="modal-overlay" id="printLedgerModal">
        <div class="modal-card print-statement-sheet" style="max-width: 900px;">
            <div class="modal-header">
                <div>
                    <h3 style="font-size:16px; font-weight:700; color:var(--text-main); display:flex; align-items:center; gap:8px;">
                        <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                        Executive Financial & Operational Ledger Statement
                    </h3>
                    <p style="font-size:12px; color:var(--text-muted);">Official audit statement prepared for executive presentation & record keeping.</p>
                </div>
                <button onclick="closePrintLedgerModal()" class="btn btn-secondary btn-sm no-print">
                    <svg class="svg-icon sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>

            <div class="modal-body" id="printStatementBody">
                <div style="text-align: center; padding: 40px; color: var(--text-muted);">Generating printable audit statement...</div>
            </div>

            <div class="modal-footer no-print">
                <button class="btn btn-secondary" onclick="closePrintLedgerModal()">Close Preview</button>
                <button class="btn btn-primary" onclick="window.print()">
                    <svg class="svg-icon" viewBox="0 0 24 24"><polyline points="6 9 6 2 18 2 18 9"/><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"/><rect x="6" y="14" width="12" height="8"/></svg>
                    Print Statement / Save PDF
                </button>
            </div>
        </div>
    </div>

    <!-- EDIT BOOK MODAL -->
    <div class="modal-overlay" id="editBookModal">
        <div class="modal-card" style="max-width: 500px;">
            <div class="modal-header">
                <h3 style="font-size:16px; font-weight:700;">Edit Catalog Book Details</h3>
                <button onclick="closeEditBookModal()" class="btn btn-secondary btn-sm">
                    <svg class="svg-icon sm" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                </button>
            </div>
            <form id="editBookForm" onsubmit="handleEditBookSubmit(event)">
                <div class="modal-body">
                    <input type="hidden" id="editBookId">
                    <div class="form-group">
                        <label class="form-label">Catalog Book Title</label>
                        <input type="text" id="editBookName" class="form-input" required>
                    </div>
                    <div class="form-group">
                        <label class="form-label">Exhibition Year</label>
                        <input type="text" id="editBookYear" class="form-input" placeholder="e.g. 2026">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Publisher / Description Notes</label>
                        <textarea id="editBookNotes" class="form-input" rows="3" placeholder="Additional notes..."></textarea>
                    </div>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" onclick="closeEditBookModal()">Cancel</button>
                    <button type="submit" class="btn btn-primary">Save Changes</button>
                </div>
            </form>
        </div>
    </div>
""")
print("Part 4a written successfully!")

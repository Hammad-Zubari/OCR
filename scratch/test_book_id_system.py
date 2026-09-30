import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app import app, get_supabase_client, create_book, update_book_details, save_supabase

def run_tests():
    print("=" * 60)
    print("RUNNING INTEGRATION TESTS: BOOK ID STRUCTURE & EDIT SYSTEM")
    print("=" * 60)

    client, error = get_supabase_client()
    if error or not client:
        print(f"[FAIL] Could not connect to Supabase: {error}")
        return

    # Clean up test records first if any
    test_ids = ["B_0127", "B_0458", "B_0912", "B_0999"]
    for tid in test_ids:
        try:
            client.table("exhibitor").delete().eq("book_id", tid).execute()
        except Exception:
            pass
        try:
            client.table("books").delete().eq("id", tid).execute()
        except Exception:
            pass

    # TEST CASE 1: Create B_0127 + China Import and Export
    print("\n--- TEST CASE 1: Create B_0127 + China Import and Export ---")
    s1, b_id1, msg1 = create_book("B_0127", "China Import and Export")
    print(f"Result: Success={s1}, Book ID={b_id1}, Message={msg1}")
    assert s1 is True, f"Failed to create B_0127: {msg1}"
    assert b_id1 == "B_0127", f"Expected B_0127, got {b_id1}"
    
    # Save some sample exhibitors for B_0127
    test_exhibitors_1 = [
        {"name": "Beijing Tech Corp", "address": "Beijing, China", "email": "info@beijingtech.cn"},
        {"name": "Shanghai Machinery", "address": "Shanghai, China", "email": "sales@shanghaimach.cn"}
    ]
    s_ex1, cnt1, ex_msg1 = save_supabase(test_exhibitors_1, "B_0127")
    print(f"Saved exhibitors for B_0127: {cnt1} records ({ex_msg1})")
    assert s_ex1 is True, f"Failed to save exhibitors for B_0127: {ex_msg1}"

    # TEST CASE 2: Create B_0458 + China Import and Export (Must be allowed with same name)
    print("\n--- TEST CASE 2: Create B_0458 + China Import and Export (Duplicate Book Name Allowed) ---")
    s2, b_id2, msg2 = create_book("B_0458", "China Import and Export")
    print(f"Result: Success={s2}, Book ID={b_id2}, Message={msg2}")
    assert s2 is True, f"Failed to create B_0458: {msg2}"
    assert b_id2 == "B_0458", f"Expected B_0458, got {b_id2}"

    test_exhibitors_2 = [
        {"name": "Guangzhou Electronics Ltd", "address": "Guangzhou, China", "email": "contact@gzelec.cn"}
    ]
    s_ex2, cnt2, ex_msg2 = save_supabase(test_exhibitors_2, "B_0458")
    print(f"Saved exhibitors for B_0458: {cnt2} records ({ex_msg2})")
    assert s_ex2 is True, f"Failed to save exhibitors for B_0458: {ex_msg2}"

    # TEST CASE 3 & 4: Search Behavior via Flask Test Client
    print("\n--- TEST CASES 3 & 4: Search Behavior (Exact Book ID vs Book Name) ---")
    with app.test_client() as c:
        with c.session_transaction() as sess:
            sess["user_id"] = "00000000-0000-0000-0000-000000000001"
            sess["email"] = "admin@example.com"
            sess["role"] = "admin"
            sess["approved"] = True

        # Search exact Book ID: "B_0127"
        res_exact = c.get("/admin/exhibitors?search=B_0127")
        data_exact = res_exact.get_json()
        print(f"Search 'B_0127': Found {data_exact.get('total')} records")
        for ex in data_exact.get("exhibitors", []):
            print(f"  - [{ex.get('book_id')}] {ex.get('name')} | Book Name: {ex.get('book_name')}")
            assert str(ex.get("book_id")) == "B_0127", f"Expected only B_0127, found {ex.get('book_id')}"

        # Search book name: "China Import and Export"
        res_name = c.get("/admin/exhibitors?search=China%20Import%20and%20Export")
        data_name = res_name.get_json()
        print(f"Search 'China Import and Export': Found {data_name.get('total')} records")
        matched_book_ids = set(str(ex.get("book_id")) for ex in data_name.get("exhibitors", []))
        print(f"Matched Book IDs in search: {matched_book_ids}")
        assert "B_0127" in matched_book_ids, "B_0127 should be returned in book name search"
        assert "B_0458" in matched_book_ids, "B_0458 should be returned in book name search"

    # TEST CASE 5: Edit B_0127 -> B_0999 (All exhibitors must be updated to B_0999)
    print("\n--- TEST CASE 5: Edit Book ID B_0127 -> B_0999 ---")
    up_success, up_msg = update_book_details("B_0127", "B_0999", "China Import and Export (Updated)")
    print(f"Update Result: Success={up_success}, Message={up_msg}")
    assert up_success is True, f"Failed to update book: {up_msg}"

    # Verify that exhibitors now point to B_0999
    ex_res = client.table("exhibitor").select("id, name, book_id").eq("book_id", "B_0999").execute()
    print(f"Exhibitors currently pointing to B_0999: {len(ex_res.data or [])} records")
    assert len(ex_res.data or []) == 2, f"Expected 2 exhibitors linked to B_0999, got {len(ex_res.data or [])}"

    # Verify old B_0127 has 0 exhibitors
    old_ex_res = client.table("exhibitor").select("id").eq("book_id", "B_0127").execute()
    assert len(old_ex_res.data or []) == 0, "Old B_0127 still has exhibitors linked!"

    # TEST CASE 6: Try changing B_0999 -> B_0458 (Must be rejected because B_0458 already exists)
    print("\n--- TEST CASE 6: Try changing B_0999 -> B_0458 (Must be rejected) ---")
    rej_success, rej_msg = update_book_details("B_0999", "B_0458", "Conflict Name")
    print(f"Conflict Test Result: Success={rej_success}, Message={rej_msg}")
    assert rej_success is False, "Expected update to fail due to ID conflict!"
    assert "already assigned" in rej_msg or "Conflict" in rej_msg or "Cannot change" in rej_msg

    # Cleanup test data
    print("\nCleaning up test records...")
    for tid in test_ids:
        try:
            client.table("exhibitor").delete().eq("book_id", tid).execute()
        except Exception:
            pass
        try:
            client.table("books").delete().eq("id", tid).execute()
        except Exception:
            pass

    print("\n" + "=" * 60)
    print("ALL 6 BOOK ID INTEGRATION TESTS PASSED SUCCESSFULLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()

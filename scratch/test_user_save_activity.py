import json
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, log_user_save_activity, get_user_save_activities, SAVE_ACTIVITY_FILE

def test_activity_logging():
    print("=== TEST 1: Direct Activity Logging ===")
    success = log_user_save_activity(
        user_id="test-user-uuid-123",
        user_email="data_entry_operator@company.com",
        book_id=99,
        book_name="ITCN Asia 2026 Directory",
        saved_count=42
    )
    assert success, "Logging should return True"
    
    activities = get_user_save_activities()
    assert len(activities) > 0, "Activities should not be empty"
    latest = activities[0]
    print("Latest Log Entry:", json.dumps(latest, indent=2))
    assert latest["user_email"] == "data_entry_operator@company.com"
    assert latest["book_name"] == "ITCN Asia 2026 Directory"
    assert latest["saved_count"] == 42
    assert "created_at_formatted" in latest
    print("[PASS] Direct logging test passed!\n")

def test_admin_api_endpoints():
    print("=== TEST 2: Admin API Endpoints via Flask Test Client ===")
    with app.test_client() as client:
        # 1. Login as admin session
        with client.session_transaction() as sess:
            sess["user_id"] = "admin-test-uuid-999"
            sess["email"] = "admin@system.com"
            sess["role"] = "admin"
            sess["approved"] = True

        # Test /admin/overview-metrics
        res = client.get("/admin/overview-metrics")
        print("Overview Metrics status:", res.status_code)
        data = res.get_json()
        print("Overview Data:", json.dumps(data, indent=2))
        assert res.status_code == 200
        assert data["success"] is True
        assert "total_saves" in data["metrics"]
        assert "recent_activities" in data["metrics"]
        assert len(data["metrics"]["recent_activities"]) > 0

        # Test /admin/save-activities
        res_act = client.get("/admin/save-activities")
        print("Save Activities status:", res_act.status_code)
        act_data = res_act.get_json()
        print("Activity Data count:", act_data["total"])
        assert res_act.status_code == 200
        assert act_data["success"] is True
        assert len(act_data["activities"]) > 0
        print("[PASS] Admin API endpoint test passed!\n")

def test_save_route_logging():
    print("=== TEST 3: User Save Route Activity Logging ===")
    with app.test_client() as client:
        # Simulate an approved user session
        with client.session_transaction() as sess:
            sess["user_id"] = "user-alice-uuid-456"
            sess["email"] = "alice@expo.com"
            sess["role"] = "user"
            sess["approved"] = True

        # Post dummy save payload (even if Supabase table save fails or succeeds, log is recorded)
        sample_records = [
            {"name": "Test Company A", "address": "Dubai, UAE", "tel": "+97150111222", "email": "info@companya.ae", "website": "https://companya.ae"},
            {"name": "Test Company B", "address": "Karachi, PK", "tel": "+92300123456", "email": "info@companyb.pk", "website": "https://companyb.pk"}
        ]
        
        res = client.post("/save-supabase", json={
            "book_name": "Gulfood 2026",
            "records": sample_records
        })
        print("Save Supabase response status:", res.status_code)
        print("Save Supabase body:", res.get_json())
        
        # Check that activities list has the new entry
        activities = get_user_save_activities()
        alice_entry = next((a for a in activities if a["user_email"] == "alice@expo.com"), None)
        if alice_entry:
            print("Found Alice's logged activity:", json.dumps(alice_entry, indent=2))
            assert alice_entry["book_name"] == "Gulfood 2026"
            assert alice_entry["saved_count"] == 2
            print("[PASS] User save route activity logging verified!")


def test_delete_activity_endpoint():
    print("=== TEST 4: Delete Save Activity Endpoint ===")
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "admin-test-uuid-999"
            sess["email"] = "admin@system.com"
            sess["role"] = "admin"
            sess["approved"] = True

        activities = get_user_save_activities()
        if activities:
            target_id = activities[0]["id"]
            del_res = client.post(f"/admin/save-activities/{target_id}/delete")
            print("Delete response:", del_res.get_json())
            assert del_res.status_code == 200
            assert del_res.get_json()["success"] is True

            updated_activities = get_user_save_activities()
            remaining_ids = [a["id"] for a in updated_activities]
            assert target_id not in remaining_ids
def test_export_book_excel():
    print("=== TEST 5: Book-Specific Excel Download ===")
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "admin-test-uuid-999"
            sess["email"] = "admin@system.com"
            sess["role"] = "admin"
            sess["approved"] = True

        # Test export for specific book_id=7
        res = client.get("/admin/export-exhibitors?book_id=7")
        print("Export status for book_id=7:", res.status_code)
        print("Content-Disposition header:", res.headers.get("Content-Disposition"))
        assert res.status_code == 200
        assert "filename=" in res.headers.get("Content-Disposition", "")
        print("[PASS] Book-specific Excel download verified!")


def test_admin_books_accurate_count():
    print("=== TEST 6: Accurate Book Records Count in /admin/books ===")
    with app.test_client() as client:
        with client.session_transaction() as sess:
            sess["user_id"] = "admin-test-uuid-999"
            sess["email"] = "admin@system.com"
            sess["role"] = "admin"
            sess["approved"] = True

        res = client.get("/admin/books")
        assert res.status_code == 200
        data = res.get_json()
        assert data["success"] is True
        books = data["books"]
        print("Fetched books count list:")
        for b in books:
            print(f"  Book #{b['id']} ({b['book_name']}): {b['exhibitor_count']} records")
            if b["id"] == 9:
                assert b["exhibitor_count"] == 14, f"Book #9 should have 14 records, got {b['exhibitor_count']}"
        print("[PASS] Accurate book counts verified!")


if __name__ == "__main__":
    test_activity_logging()
    test_admin_api_endpoints()
    test_save_route_logging()
    test_delete_activity_endpoint()
    test_export_book_excel()
    test_admin_books_accurate_count()
    print("ALL TESTS PASSED SUCCESSFULLY!")





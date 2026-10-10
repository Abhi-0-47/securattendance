from starlette.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)

    # 1. Test Index
    r = client.get("/")
    assert r.status_code == 200, f"Index failed: {r.status_code}"
    print("[OK] Test 1 Passed: Index HTML served successfully.")

    # 2. Test Workers
    r = client.get("/api/v1/workers")
    assert r.status_code == 200
    data = r.json()
    assert data["count"] >= 5
    print(f"[OK] Test 2 Passed: Enrolled {data['count']} Indian daily wage worker profiles.")

    # 3. Test Punch-in Live
    r = client.post("/api/v1/attendance/punch-in", json={
        "worker_id": "WRK-MH-1042",
        "shifts_worked": 1.0,
        "capture_type": "LIVE",
        "pad_override_spoof": False
    })
    assert r.status_code == 200
    p = r.json()
    assert p["biometric_result"]["is_live"] is True
    assert p["committed_record"] is not None
    print(f"[OK] Test 3 Passed: Live Punch-In validated, PAD score={p['biometric_result']['pad_score']}, committed muster record #{p['committed_record']['record_id']}.")

    # 4. Test Punch-in Proxy Spoof Block
    r = client.post("/api/v1/attendance/punch-in", json={
        "worker_id": "WRK-MH-1042",
        "shifts_worked": 1.0,
        "capture_type": "PRINT_2D",
        "pad_override_spoof": False
    })
    assert r.status_code == 200
    p = r.json()
    assert p["biometric_result"]["is_live"] is False
    assert p["committed_record"] is None
    print("[OK] Test 4 Passed: 2D Contractor Proxy Spoof intercepted and dropped by PAD Sentinel.")

    # 5. Test Ledger Initial Total (5 records: ₹750 + ₹700 + ₹800 + ₹850 + ₹750 = ₹3850)
    r = client.get("/api/v1/ledger")
    assert r.status_code == 200
    ledger_data = r.json()
    initial_total_wage = ledger_data["total_wage"]
    assert initial_total_wage == 3850.0
    print(f"[OK] Test 5 Passed: Initial pristine ledger has {ledger_data['records_count']} blocks, certified wage={initial_total_wage} INR.")

    # 6. Test Merkle Tree
    r = client.get("/api/v1/merkle-tree")
    assert r.status_code == 200
    tree_data = r.json()
    print(f"[OK] Test 6 Passed: Merkle Tree compiled with root: {tree_data['root'][:16]}...")

    # 7. Test Pristine Audit
    r = client.post("/api/v1/ledger/audit")
    assert r.status_code == 200
    audit = r.json()
    assert audit["is_valid"] is True
    print("[OK] Test 7 Passed: Initial cryptographic audit passed with 100% muster continuity.")

    # 8. Test Isolated Block Tamper Simulation (Tamper ONLY Block #2)
    # Ramesh Patil daily rate is ₹700. Altering shifts to 3.0 gives forged wage of ₹2100.
    r = client.post("/api/v1/ledger/tamper", json={"record_id": 2, "forged_shifts": 3.0})
    assert r.status_code == 200

    # Verify isolated block-by-block integrity:
    # Only Block #2 is tampered! Blocks #1, #3, #4, #5 remain genuine and valid.
    # Certified wage must dynamically sum all valid blocks: ₹750 + ₹800 + ₹850 + ₹750 = ₹3150.0
    # Blocked wage is strictly the forged Block #2: ₹2100.0
    r_ledger_tampered = client.get("/api/v1/ledger")
    tampered_ledger_data = r_ledger_tampered.json()
    assert tampered_ledger_data["is_ledger_valid"] is False
    assert tampered_ledger_data["total_wage"] == 3150.0, f"Expected 3150.0 certified, got {tampered_ledger_data['total_wage']}"
    assert tampered_ledger_data["blocked_corrupted_wage"] == 2100.0, f"Expected 2100.0 blocked, got {tampered_ledger_data['blocked_corrupted_wage']}"
    assert tampered_ledger_data["verified_records_count"] == 4
    assert tampered_ledger_data["tampered_records_count"] == 1
    assert 2 in tampered_ledger_data["corrupted_record_ids"]

    # Verify individual blocks status
    records = tampered_ledger_data["records"]
    assert records[0]["is_valid"] is True   # Block 1: Rajesh Kumar
    assert records[1]["is_valid"] is False  # Block 2: Ramesh Patil (Tampered)
    assert records[1]["is_corrupted"] is True
    assert records[2]["is_valid"] is True   # Block 3: Sunita Devi (Genuine & Valid!)
    assert records[3]["is_valid"] is True   # Block 4: Mohammed Farooq (Genuine & Valid!)
    assert records[4]["is_valid"] is True   # Block 5: Rajesh Kumar (Genuine & Valid!)

    print(f"[OK] Test 8 Passed: Isolated Block Integrity Verified!")
    print(f"     -> Block #2 successfully isolated and excluded (Blocked: INR {tampered_ledger_data['blocked_corrupted_wage']})")
    print(f"     -> Blocks #1, #3, #4, #5 remain genuine & verified (Certified: INR {tampered_ledger_data['total_wage']})")

    # 9. Test Reset
    r = client.post("/api/v1/ledger/reset")
    assert r.status_code == 200
    r = client.post("/api/v1/ledger/audit")
    audit = r.json()
    assert audit["is_valid"] is True
    print("[OK] Test 9 Passed: Ledger reset restored pristine certified muster roll.")

    # 10. Test Queue telemetry
    r = client.get("/api/v1/queue/metrics")
    assert r.status_code == 200
    m = r.json()
    print(f"[OK] Test 10 Passed: Queue telemetry active. Avg E2E Latency: {m['avg_total_e2e_latency_ms']}ms.")

    print("\n=======================================================")
    print("ALL TESTS COMPLETED SUCCESSFULLY! PROTOTYPE FULLY OPERATIONAL.")
    print("=======================================================\n")

if __name__ == "__main__":
    run_tests()

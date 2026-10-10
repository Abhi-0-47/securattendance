"""
Main FastAPI Application
"SecurAttendance: Multimodal Biometric Attendance Framework with Cryptographic Wage Auditing"
Tailored for Indian Daily Wage & Construction/Infrastructure Labor Protection.
Features isolated block-level integrity auditing and dynamic wage aggregation.
"""

import os
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.crypto_ledger import CryptoLedger
from app.biometric_pad import BiometricPADService
from app.queue_simulator import CloudQueueSimulator

app = FastAPI(
    title="SecurAttendance: Daily Wage Attendance & Cryptographic Muster Auditing",
    description="Research prototype securing Indian daily wage workers against ghost-worker fraud and payroll tampering.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ledger = CryptoLedger()
queue_sim = CloudQueueSimulator()


class PunchInRequest(BaseModel):
    worker_id: Optional[str] = Field(None, example="WRK-MH-1042")
    emp_id: Optional[str] = None
    shifts_worked: Optional[float] = Field(1.0, ge=0.25, le=3.0)
    hours_worked: Optional[float] = None
    capture_type: str = Field("LIVE", example="LIVE")
    pad_override_spoof: bool = Field(False)


class TamperRequest(BaseModel):
    record_id: int = Field(..., ge=1)
    forged_shifts: Optional[float] = None
    forged_hours: Optional[float] = None
    forged_wage: Optional[float] = None


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")

if os.path.exists(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/", include_in_schema=False)
def serve_index():
    index_path = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SecurAttendance UI active. Access /docs for API."}


@app.get("/api/v1/workers", summary="Get Enrolled Indian Labor Registry")
@app.get("/api/v1/employees", summary="Alias for Enrolled Worker Registry")
def get_workers():
    workers_list = [w.model_dump() for w in BiometricPADService.ENROLLED_WORKERS]
    for w in workers_list:
        w["emp_id"] = w["worker_id"]
        w["role"] = w["trade"]
        w["hourly_rate"] = round(w["daily_wage_rate"] / 8.0, 2)
        w["department"] = w["worksite_location"]
        w["template_hash"] = w["aadhaar_ref_hash"]
        w["avatar_color"] = "from-slate-700 to-slate-900"
    return {
        "count": len(workers_list),
        "workers": workers_list,
        "employees": workers_list,
    }


@app.post("/api/v1/attendance/punch-in", summary="Process Daily Shift Check-In")
def punch_in(req: PunchInRequest):
    wid = req.worker_id or req.emp_id or "WRK-MH-1042"
    shifts = req.shifts_worked if req.shifts_worked is not None else (round(req.hours_worked / 8.0, 2) if req.hours_worked else 1.0)

    worker = BiometricPADService.get_worker(wid)
    if not worker:
        worker = BiometricPADService.ENROLLED_WORKERS[0]

    # 1. AI/ML: Multi-Spectral Liveness & Presentation Attack Detection
    bio_res = BiometricPADService.analyze_capture(
        worker_id=worker.worker_id,
        capture_type=req.capture_type,
        pad_override_spoof=req.pad_override_spoof,
    )

    # 2. Cloud Ingestion: Redis Stream Push & Celery Worker Execution
    queue_result = queue_sim.process_punch_in_pipeline(
        worker_id=worker.worker_id,
        worker_name=worker.name,
        trade=worker.trade,
        site_location=worker.worksite_location,
        shifts_worked=shifts,
        daily_wage_rate=worker.daily_wage_rate,
        biometric_res=bio_res.model_dump(),
    )

    new_record = None
    if bio_res.is_live:
        # 3. Security Track: Commit Shift Record into SHA-256 Ledger
        new_record = ledger.append_record(
            worker_id=worker.worker_id,
            worker_name=worker.name,
            trade=worker.trade,
            site_location=worker.worksite_location,
            shifts_worked=shifts,
            daily_wage_rate=worker.daily_wage_rate,
            biometric_proof=bio_res.proof_token,
            pad_status=bio_res.status,
        )

    tree_data = ledger.build_merkle_tree()
    audit = ledger.audit_verification()

    rec_dump = new_record.model_dump() if new_record else None
    if rec_dump:
        rec_dump["emp_id"] = rec_dump["worker_id"]
        rec_dump["emp_name"] = rec_dump["worker_name"]
        rec_dump["role"] = rec_dump["trade"]
        rec_dump["hours_worked"] = round(rec_dump["shifts_worked"] * 8.0, 1)
        rec_dump["hourly_rate"] = round(rec_dump["daily_wage_rate"] / 8.0, 2)

    return {
        "status": "PROCESSED",
        "biometric_result": bio_res.model_dump(),
        "cloud_queue_pipeline": queue_result,
        "committed_record": rec_dump,
        "ledger_summary": {
            "total_records": len(ledger.records),
            "merkle_root": tree_data["root"],
            "total_certified_wage_inr": audit.total_audited_wage,
            "blocked_corrupted_wage_inr": audit.blocked_corrupted_wage,
        },
    }


@app.get("/api/v1/ledger", summary="Get Daily Wage Muster Ledger State")
def get_ledger():
    tree = ledger.build_merkle_tree()
    audit = ledger.audit_verification()

    # Dynamic block-by-block aggregation:
    # Only genuine un-tampered blocks contribute to certified_wage!
    certified_wage = audit.total_audited_wage
    blocked_corrupted_wage = audit.blocked_corrupted_wage

    records_dump = []
    verified_shifts = 0.0

    for idx, r in enumerate(ledger.records):
        detail = audit.chain_details[idx]
        is_block_valid = detail["is_valid"]

        if is_block_valid:
            verified_shifts += r.shifts_worked

        d = r.model_dump()
        d["is_valid"] = is_block_valid
        d["is_corrupted"] = detail["status"] == "CORRUPTED_PAYLOAD"
        d["is_downstream_broken"] = detail["status"] == "BROKEN_CHAIN"
        d["mismatch_type"] = detail["mismatch_type"]
        d["emp_id"] = d["worker_id"]
        d["emp_name"] = d["worker_name"]
        d["role"] = d["trade"]
        d["hours_worked"] = round(d["shifts_worked"] * 8.0, 1)
        d["hourly_rate"] = round(d["daily_wage_rate"] / 8.0, 2)
        records_dump.append(d)

    return {
        "records_count": len(ledger.records),
        "verified_records_count": audit.verified_records_count,
        "tampered_records_count": audit.tampered_records_count,
        "is_ledger_valid": audit.is_valid,
        "corrupted_record_ids": audit.corrupted_record_ids,
        "broken_record_id": audit.broken_record_id,
        "failure_reason": audit.failure_reason,
        "total_wage": certified_wage,  # Strictly sum of genuine verified blocks!
        "total_wage_inr": f"₹{certified_wage:,.2f}",
        "blocked_corrupted_wage": blocked_corrupted_wage,
        "blocked_corrupted_wage_inr": f"₹{blocked_corrupted_wage:,.2f}",
        "total_shifts": round(verified_shifts, 2),
        "genesis_hash": CryptoLedger.GENESIS_HASH,
        "current_merkle_root": tree["root"],
        "last_certified_merkle_root": ledger.last_certified_merkle_root,
        "records": records_dump,
    }


@app.get("/api/v1/merkle-tree", summary="Get Muster Roll Merkle Tree")
def get_merkle_tree():
    return ledger.build_merkle_tree()


@app.post("/api/v1/ledger/tamper", summary="Simulate Contractor Muster Tampering")
def tamper_ledger(req: TamperRequest):
    try:
        shifts = req.forged_shifts
        if shifts is None and req.forged_hours is not None:
            shifts = round(req.forged_hours / 8.0, 2)
        if shifts is None:
            shifts = 2.5

        res = ledger.tamper_record(
            record_id=req.record_id,
            forged_shifts=shifts,
            forged_wage=req.forged_wage,
        )
        return {"status": "TAMPERED", "details": res}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/v1/ledger/audit", summary="Run Cryptographic Muster Verification")
def run_audit():
    audit_res = ledger.audit_verification()
    d = audit_res.model_dump()
    for c in d["chain_details"]:
        c["emp_id"] = c["worker_id"]
        c["emp_name"] = c["worker_name"]
        c["role"] = c["trade"]
        c["hours_worked"] = round(c["shifts_worked"] * 8.0, 1)
        c["hourly_rate"] = round(c["daily_wage_rate"] / 8.0, 2)
    return d


@app.post("/api/v1/ledger/reset", summary="Reset Ledger to Initial Certified Muster")
def reset_ledger():
    ledger.restore_and_reseed()
    tree = ledger.build_merkle_tree()
    return {
        "status": "RESTORED",
        "records_count": len(ledger.records),
        "merkle_root": tree["root"],
        "message": "Muster ledger and Merkle root have been restored to certified initial state.",
    }


@app.get("/api/v1/queue/logs", summary="Get Worksites Ingestion Activity Logs")
def get_queue_logs(limit: int = 35):
    return {"logs": queue_sim.get_logs(limit=limit)}


@app.get("/api/v1/queue/metrics", summary="Get Cloud Ingestion Telemetry")
def get_queue_metrics():
    return queue_sim.get_metrics().model_dump()

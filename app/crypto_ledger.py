"""
Cryptographic Ledger & Merkle Tree Rollup Engine
Designed for Daily Wage & Blue-Collar Labor Muster Roll Auditing in India.
Implements SHA-256 hash-chained shift logging and Merkle root verification.
Features isolated block-level integrity verification and dynamic wage aggregation.
"""

import hashlib
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel


class ShiftRecord(BaseModel):
    record_id: int
    timestamp: str
    worker_id: str
    worker_name: str
    trade: str               # e.g., "Senior Mason (Rajmistri)", "Steel Rebar Fabricator"
    site_location: str       # e.g., "Site #MH-04: Metro Phase-3, Mumbai"
    shifts_worked: float     # e.g., 1.0 (Full Shift - 8h), 0.5 (Half Day), 1.5 (Shift + Overtime)
    daily_wage_rate: float   # in INR (₹)
    calculated_wage: float   # in INR (₹)
    biometric_proof: str     # Hash of biometric PAD verification & timestamp
    pad_status: str          # "LIVE_CONFIRMED"
    prev_hash: str
    record_hash: str


class AuditResult(BaseModel):
    is_valid: bool
    tampered_records_count: int = 0
    corrupted_record_ids: List[int] = []
    broken_record_id: Optional[int] = None
    failure_reason: Optional[str] = None
    tampered_field: Optional[str] = None
    stored_hash: Optional[str] = None
    recomputed_hash: Optional[str] = None
    merkle_root_matches: bool
    expected_merkle_root: str
    computed_merkle_root: str
    total_audited_wage: float       # Dynamically sums ONLY genuine verified blocks
    blocked_corrupted_wage: float   # Sums isolated tampered blocks
    verified_records_count: int     # Count of genuine verified blocks
    total_records_count: int        # Total blocks in ledger
    chain_details: List[Dict[str, Any]]


class CryptoLedger:
    GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

    def __init__(self):
        self.records: List[ShiftRecord] = []
        self.last_certified_merkle_root: str = ""
        self._seed_initial_records()

    @staticmethod
    def compute_sha256(data: str) -> str:
        return hashlib.sha256(data.encode("utf-8")).hexdigest()

    @staticmethod
    def canonical_payload(
        record_id: int,
        timestamp: str,
        worker_id: str,
        worker_name: str,
        trade: str,
        site_location: str,
        shifts_worked: float,
        daily_wage_rate: float,
        calculated_wage: float,
        biometric_proof: str,
        pad_status: str,
        prev_hash: str,
    ) -> str:
        """Deterministic canonical representation for cryptographic hashing."""
        payload = {
            "record_id": record_id,
            "timestamp": timestamp,
            "worker_id": worker_id,
            "worker_name": worker_name,
            "trade": trade,
            "site_location": site_location,
            "shifts_worked": round(shifts_worked, 2),
            "daily_wage_rate": round(daily_wage_rate, 2),
            "calculated_wage": round(calculated_wage, 2),
            "biometric_proof": biometric_proof,
            "pad_status": pad_status,
            "prev_hash": prev_hash,
        }
        return json.dumps(payload, sort_keys=True)

    def append_record(
        self,
        worker_id: str,
        worker_name: str,
        trade: str,
        site_location: str,
        shifts_worked: float,
        daily_wage_rate: float,
        biometric_proof: str,
        pad_status: str = "LIVE_CONFIRMED",
        timestamp: Optional[str] = None,
    ) -> ShiftRecord:
        record_id = len(self.records) + 1
        if not timestamp:
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S IST", time.localtime())

        prev_hash = self.records[-1].record_hash if self.records else self.GENESIS_HASH
        calculated_wage = round(shifts_worked * daily_wage_rate, 2)

        canonical_data = self.canonical_payload(
            record_id=record_id,
            timestamp=timestamp,
            worker_id=worker_id,
            worker_name=worker_name,
            trade=trade,
            site_location=site_location,
            shifts_worked=shifts_worked,
            daily_wage_rate=daily_wage_rate,
            calculated_wage=calculated_wage,
            biometric_proof=biometric_proof,
            pad_status=pad_status,
            prev_hash=prev_hash,
        )
        record_hash = self.compute_sha256(canonical_data)

        new_record = ShiftRecord(
            record_id=record_id,
            timestamp=timestamp,
            worker_id=worker_id,
            worker_name=worker_name,
            trade=trade,
            site_location=site_location,
            shifts_worked=shifts_worked,
            daily_wage_rate=daily_wage_rate,
            calculated_wage=calculated_wage,
            biometric_proof=biometric_proof,
            pad_status=pad_status,
            prev_hash=prev_hash,
            record_hash=record_hash,
        )
        self.records.append(new_record)
        tree = self.build_merkle_tree()
        self.last_certified_merkle_root = tree["root"]
        return new_record

    def build_merkle_tree(self) -> Dict[str, Any]:
        """
        Constructs a binary Merkle Tree from the muster roll record hashes.
        Returns tree levels and the Merkle Root for daily/weekly muster roll verification.
        """
        if not self.records:
            return {"root": self.GENESIS_HASH, "levels": [], "tree_nodes": []}

        leaf_nodes = []
        for rec in self.records:
            leaf_nodes.append({
                "hash": rec.record_hash,
                "label": f"Muster #{rec.record_id} ({rec.worker_name.split()[0]})",
                "is_leaf": True,
                "record_id": rec.record_id,
                "wage": rec.calculated_wage,
            })

        levels = [leaf_nodes]
        current_level = leaf_nodes

        level_idx = 0
        while len(current_level) > 1:
            next_level = []
            for i in range(0, len(current_level), 2):
                left = current_level[i]
                if i + 1 < len(current_level):
                    right = current_level[i + 1]
                else:
                    right = left

                combined_data = left["hash"] + right["hash"]
                parent_hash = self.compute_sha256(combined_data)
                next_level.append({
                    "hash": parent_hash,
                    "label": f"Rollup L{level_idx + 1}_{len(next_level)}",
                    "left": left["hash"],
                    "right": right["hash"],
                    "is_leaf": False,
                    "level": level_idx + 1,
                })
            levels.append(next_level)
            current_level = next_level
            level_idx += 1

        root_hash = current_level[0]["hash"] if current_level else self.GENESIS_HASH

        return {
            "root": root_hash,
            "levels": levels,
            "total_leaves": len(leaf_nodes),
            "tree_height": len(levels),
        }

    def tamper_record(self, record_id: int, forged_shifts: float, forged_wage: Optional[float] = None) -> Dict[str, Any]:
        """
        Simulate labor muster-roll tampering:
        A corrupt contractor or site clerk inflates shifts or siphons wages
        directly in the database without cryptographic re-computation.
        """
        target = None
        for rec in self.records:
            if rec.record_id == record_id:
                target = rec
                break

        if not target:
            raise ValueError(f"Muster Record #{record_id} not found in ledger.")

        original_shifts = target.shifts_worked
        original_wage = target.calculated_wage

        target.shifts_worked = forged_shifts
        target.calculated_wage = forged_wage if forged_wage is not None else round(forged_shifts * target.daily_wage_rate, 2)

        return {
            "tampered_record_id": record_id,
            "original_shifts": original_shifts,
            "original_wage": original_wage,
            "forged_shifts": target.shifts_worked,
            "forged_wage": target.calculated_wage,
            "message": f"Muster Record #{record_id} ({target.worker_name}) maliciously altered: shifts {original_shifts} -> {target.shifts_worked} (Wage: ₹{original_wage} -> ₹{target.calculated_wage}).",
        }

    def audit_verification(self) -> AuditResult:
        """
        Strictly block-by-block integrity verification & dynamic financial aggregation:
        1. Evaluates each block independently:
           - Recomputed local canonical payload hash == rec.record_hash
           - Predecessor linkage: rec.prev_hash == predecessor's stored record_hash
        2. Isolates corrupted records:
           - Tampered blocks are individually flagged and excluded from Certified Wage Entitlement.
           - Genuine un-tampered blocks (both before and after) verify their own hashes and remain valid.
        3. Financial summation:
           - total_audited_wage dynamically sums ONLY genuine un-tampered blocks.
           - blocked_corrupted_wage sums isolated fraudulent/corrupted blocks.
        """
        chain_details = []
        corrupted_ids = []
        total_valid_wage = 0.0
        corrupted_wage_blocked = 0.0
        primary_failure_reason = None
        first_stored_hash = None
        first_recomputed_hash = None

        for idx, rec in enumerate(self.records):
            expected_prev = self.records[idx - 1].record_hash if idx > 0 else self.GENESIS_HASH

            canonical_data = self.canonical_payload(
                record_id=rec.record_id,
                timestamp=rec.timestamp,
                worker_id=rec.worker_id,
                worker_name=rec.worker_name,
                trade=rec.trade,
                site_location=rec.site_location,
                shifts_worked=rec.shifts_worked,
                daily_wage_rate=rec.daily_wage_rate,
                calculated_wage=rec.calculated_wage,
                biometric_proof=rec.biometric_proof,
                pad_status=rec.pad_status,
                prev_hash=rec.prev_hash,
            )
            recalculated_hash = self.compute_sha256(canonical_data)

            is_block_valid = True
            record_status = "VALID"
            mismatch_type = None

            # Check 1: Block payload hash integrity (did anyone alter hours/wage/id?)
            if recalculated_hash != rec.record_hash:
                is_block_valid = False
                record_status = "CORRUPTED_PAYLOAD"
                mismatch_type = "Payload altered (Shift/Wage Tampering)"
                corrupted_ids.append(rec.record_id)
                if not primary_failure_reason:
                    primary_failure_reason = f"Hash Mismatch in Shift #{rec.record_id} ({rec.worker_name}): Recalculated hash does not match stored block hash. Unauthorized shift modification detected."
                    first_stored_hash = rec.record_hash
                    first_recomputed_hash = recalculated_hash

            # Check 2: Predecessor hash continuity (did anyone inject/delete a block?)
            elif rec.prev_hash != expected_prev:
                is_block_valid = False
                record_status = "BROKEN_CHAIN"
                mismatch_type = "Predecessor Hash Discontinuity"
                corrupted_ids.append(rec.record_id)
                if not primary_failure_reason:
                    primary_failure_reason = f"Chain Discontinuity in Shift #{rec.record_id}: prev_hash does not match Shift #{self.records[idx-1].record_id} hash."
                    first_stored_hash = rec.prev_hash
                    first_recomputed_hash = expected_prev

            # Dynamic financial aggregation: Sum ONLY genuine verified blocks!
            if is_block_valid:
                total_valid_wage += rec.calculated_wage
            else:
                corrupted_wage_blocked += rec.calculated_wage

            chain_details.append({
                "record_id": rec.record_id,
                "worker_id": rec.worker_id,
                "worker_name": rec.worker_name,
                "trade": rec.trade,
                "site_location": rec.site_location,
                "shifts_worked": rec.shifts_worked,
                "daily_wage_rate": rec.daily_wage_rate,
                "calculated_wage": rec.calculated_wage,
                "stored_hash": rec.record_hash,
                "recomputed_hash": recalculated_hash,
                "stored_prev_hash": rec.prev_hash,
                "expected_prev_hash": expected_prev,
                "is_valid": is_block_valid,
                "is_corrupted": not is_block_valid,
                "status": record_status,
                "mismatch_type": mismatch_type,
            })

        is_overall_valid = len(corrupted_ids) == 0
        current_merkle_tree = self.build_merkle_tree()
        computed_root = current_merkle_tree["root"]
        merkle_matches = (computed_root == self.last_certified_merkle_root) and is_overall_valid

        return AuditResult(
            is_valid=is_overall_valid,
            tampered_records_count=len(corrupted_ids),
            corrupted_record_ids=corrupted_ids,
            broken_record_id=corrupted_ids[0] if corrupted_ids else None,
            failure_reason=primary_failure_reason,
            tampered_field="shifts_worked / calculated_wage" if not is_overall_valid else None,
            stored_hash=first_stored_hash,
            recomputed_hash=first_recomputed_hash,
            merkle_root_matches=merkle_matches,
            expected_merkle_root=self.last_certified_merkle_root,
            computed_merkle_root=computed_root,
            total_audited_wage=round(total_valid_wage, 2),
            blocked_corrupted_wage=round(corrupted_wage_blocked, 2),
            verified_records_count=len(self.records) - len(corrupted_ids),
            total_records_count=len(self.records),
            chain_details=chain_details,
        )

    def restore_and_reseed(self):
        """Restore pristine, un-tampered demo state."""
        self.records.clear()
        self._seed_initial_records()

    def _seed_initial_records(self):
        """Pre-populate realistic Indian construction and field worker records."""
        seeds = [
            ("WRK-MH-1042", "Rajesh Kumar", "Senior Mason (Rajmistri)", "Site #MH-04: Metro Depot, Mumbai", 1.0, 750.0, "2026-10-10 08:02:14 IST"),
            ("WRK-MH-2089", "Ramesh Patil", "Steel Rebar Fabricator", "Site #MH-04: Metro Depot, Mumbai", 1.0, 700.0, "2026-10-10 08:15:30 IST"),
            ("WRK-MH-3310", "Sunita Devi", "Excavator & Heavy Machinery", "Site #MH-04: Metro Depot, Mumbai", 1.0, 800.0, "2026-10-10 08:28:45 IST"),
            ("WRK-MH-4105", "Mohammed Farooq", "Master Site Electrician", "Site #MH-04: Metro Depot, Mumbai", 1.0, 850.0, "2026-10-10 08:40:19 IST"),
        ]

        for worker_id, worker_name, trade, site, shifts, wage_rate, ts in seeds:
            proof = self.compute_sha256(f"{worker_id}:{ts}:BIOMETRIC_PAD_CONFIRMED")
            self.append_record(
                worker_id=worker_id,
                worker_name=worker_name,
                trade=trade,
                site_location=site,
                shifts_worked=shifts,
                daily_wage_rate=wage_rate,
                biometric_proof=proof,
                pad_status="LIVE_CONFIRMED",
                timestamp=ts,
            )

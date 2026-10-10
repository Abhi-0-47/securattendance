"""
Cloud Ingestion & Async Worker Queue Simulator
Simulates Worksites Edge Device -> FastAPI Gateway -> Redis Broker -> Celery Worker
for large-scale daily wage muster roll processing across Indian infrastructure projects.
"""

import time
import uuid
import random
from typing import Dict, Any, List
from pydantic import BaseModel


class QueueEventLog(BaseModel):
    event_id: str
    timestamp: str
    phase: str
    node: str
    status: str
    latency_ms: float
    message: str
    payload: Dict[str, Any]


class QueueMetrics(BaseModel):
    total_requests_ingested: int
    successful_punches: int
    blocked_spoof_attempts: int
    avg_gateway_latency_ms: float
    avg_redis_queue_latency_ms: float
    avg_celery_worker_latency_ms: float
    avg_total_e2e_latency_ms: float
    current_redis_queue_depth: int
    active_celery_workers: int
    worker_node_id: str


class CloudQueueSimulator:
    def __init__(self):
        self.logs: List[QueueEventLog] = []
        self.total_requests = 0
        self.successful_punches = 4
        self.blocked_spoofs = 0
        self.gateway_latencies: List[float] = [7.8, 8.4, 8.1, 7.9]
        self.redis_latencies: List[float] = [11.5, 12.0, 10.8, 11.2]
        self.celery_latencies: List[float] = [43.5, 46.2, 41.8, 44.1]
        self.e2e_latencies: List[float] = [95.0, 101.2, 94.3, 96.8]
        self.worker_id = "celery@node-mumbai-depot-01"
        self._seed_initial_logs()

    def _seed_initial_logs(self):
        """Seed initial pipeline logs for the Worksites Cloud Ingestion stream."""
        past_time = time.strftime("%H:%M:%S", time.localtime(time.time() - 240))
        self.logs.append(QueueEventLog(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=past_time,
            phase="WORK_SITE_READY",
            node="Site Terminal #MH-04",
            status="CONNECTED",
            latency_ms=1.1,
            message="Site Terminal (Metro Depot Mumbai) linked to FastAPI Cloud Gateway. Redis muster stream active.",
            payload={"site_id": "Site-MH-04", "broker": "redis://cloud.infra.gov.in:6379/0", "workers": 4},
        ))

    def process_punch_in_pipeline(
        self,
        worker_id: str,
        worker_name: str,
        trade: str,
        site_location: str,
        shifts_worked: float,
        daily_wage_rate: float,
        biometric_res: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Executes sub-second simulated FastAPI -> Redis Queue -> Celery Worker execution pipeline.
        """
        req_id = f"req_{uuid.uuid4().hex[:8]}"
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        now_str = time.strftime("%H:%M:%S", time.localtime())

        gw_lat = round(random.uniform(6.5, 11.2), 2)
        redis_lat = round(random.uniform(9.5, 15.0), 2)
        celery_proc_lat = round(biometric_res.get("inference_time_ms", 42.0) + random.uniform(12.0, 20.0), 2)
        ledger_lat = round(random.uniform(7.5, 14.0), 2) if biometric_res["is_live"] else 1.2
        total_e2e = round(gw_lat + redis_lat + celery_proc_lat + ledger_lat, 2)

        self.total_requests += 1
        self.gateway_latencies.append(gw_lat)
        self.redis_latencies.append(redis_lat)
        self.celery_latencies.append(celery_proc_lat)
        self.e2e_latencies.append(total_e2e)

        if biometric_res["is_live"]:
            self.successful_punches += 1
        else:
            self.blocked_spoofs += 1

        events_generated: List[QueueEventLog] = []

        # 1. FastAPI Gateway Ingestion
        e1 = QueueEventLog(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=now_str,
            phase="FASTAPI_INGESTION",
            node="FastAPI Ingestion Gateway (POST /punch-in)",
            status="ACCEPTED_202",
            latency_ms=gw_lat,
            message=f"Received shift check-in payload for {worker_name} ({worker_id}) from {site_location}. Payload validated.",
            payload={
                "endpoint": "/api/v1/attendance/punch-in",
                "worker_id": worker_id,
                "shifts_worked": shifts_worked,
                "correlation_id": req_id,
            },
        )
        events_generated.append(e1)

        # 2. Redis Message Broker Enqueue
        e2 = QueueEventLog(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=now_str,
            phase="REDIS_BROKER",
            node="Redis Muster Stream (stream:muster_roll)",
            status="ENQUEUED",
            latency_ms=redis_lat,
            message=f"Pushed to Redis FIFO queue 'stream:muster_roll'. Assigned Celery Task: {task_id}.",
            payload={
                "stream_topic": "attendance:muster_roll",
                "task_id": task_id,
                "queue_depth": 1,
            },
        )
        events_generated.append(e2)

        # 3. Celery Distributed Worker Execution
        worker_status = "PAD_CONFIRMED" if biometric_res["is_live"] else "PAD_SPOOF_REJECTED"
        e3 = QueueEventLog(
            event_id=f"evt_{uuid.uuid4().hex[:8]}",
            timestamp=now_str,
            phase="CELERY_WORKER",
            node=self.worker_id,
            status=worker_status,
            latency_ms=celery_proc_lat,
            message=(
                f"Celery worker executed PAD multi-spectral inference. "
                f"Score: {biometric_res['pad_score']} (Threshold: {biometric_res['threshold']}). "
                f"Result: {biometric_res['status']}."
            ),
            payload={
                "task_id": task_id,
                "pad_score": biometric_res["pad_score"],
                "liveness_outcome": biometric_res["status"],
                "attack_vector": biometric_res.get("attack_type", "None"),
            },
        )
        events_generated.append(e3)

        # 4. Cryptographic Ledger Persist or Drop
        if biometric_res["is_live"]:
            calculated_wage = round(shifts_worked * daily_wage_rate, 2)
            e4 = QueueEventLog(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                timestamp=now_str,
                phase="CRYPTOGRAPHIC_LEDGER",
                node="Muster Ledger Service",
                status="HASH_CHAINED_&_SEALED",
                latency_ms=ledger_lat,
                message=f"Shift record committed to SHA-256 chain. Credited ₹{calculated_wage:.2f}. Merkle epoch root updated.",
                payload={
                    "worker_id": worker_id,
                    "shifts": shifts_worked,
                    "wage_inr": f"₹{calculated_wage:.2f}",
                    "proof_token": biometric_res.get("proof_token", "")[:24] + "...",
                },
            )
        else:
            e4 = QueueEventLog(
                event_id=f"evt_{uuid.uuid4().hex[:8]}",
                timestamp=now_str,
                phase="SECURITY_AUDIT_LOG",
                node="Ghost-Worker Sentinel",
                status="MUSTER_PUNCH_DROPPED",
                latency_ms=ledger_lat,
                message=f"Presentation Attack Blocked! Fake check-in discarded. ₹0.00 wage credited. Incident flagged for site inspector.",
                payload={
                    "threat": "CONTRACTOR_BUDDY_PUNCH_OR_GHOST_WORKER",
                    "attack_type": biometric_res.get("attack_type"),
                    "action": "ZERO_WAGE_CREDITED",
                },
            )
        events_generated.append(e4)

        for ev in reversed(events_generated):
            self.logs.insert(0, ev)

        if len(self.logs) > 60:
            self.logs = self.logs[:60]

        return {
            "req_id": req_id,
            "task_id": task_id,
            "total_e2e_latency_ms": total_e2e,
            "pipeline_stages": [
                {"stage": "FastAPI Gateway", "latency_ms": gw_lat, "status": "202 Accepted"},
                {"stage": "Redis Stream Broker", "latency_ms": redis_lat, "status": "Delivered"},
                {"stage": "Celery PAD Worker", "latency_ms": celery_proc_lat, "status": worker_status},
                {"stage": "Ledger & Merkle Rollup", "latency_ms": ledger_lat, "status": "Committed" if biometric_res["is_live"] else "Dropped"},
            ],
            "recent_events": [ev.model_dump() for ev in events_generated],
        }

    def get_metrics(self) -> QueueMetrics:
        avg_gw = round(sum(self.gateway_latencies) / max(1, len(self.gateway_latencies)), 2)
        avg_rd = round(sum(self.redis_latencies) / max(1, len(self.redis_latencies)), 2)
        avg_cl = round(sum(self.celery_latencies) / max(1, len(self.celery_latencies)), 2)
        avg_e2e = round(sum(self.e2e_latencies) / max(1, len(self.e2e_latencies)), 2)

        return QueueMetrics(
            total_requests_ingested=self.total_requests + 4,
            successful_punches=self.successful_punches,
            blocked_spoof_attempts=self.blocked_spoofs,
            avg_gateway_latency_ms=avg_gw,
            avg_redis_queue_latency_ms=avg_rd,
            avg_celery_worker_latency_ms=avg_cl,
            avg_total_e2e_latency_ms=avg_e2e,
            current_redis_queue_depth=0,
            active_celery_workers=4,
            worker_node_id=self.worker_id,
        )

    def get_logs(self, limit: int = 35) -> List[Dict[str, Any]]:
        return [log.model_dump() for log in self.logs[:limit]]

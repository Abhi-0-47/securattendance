/**
 * SecurAttendance - Multi-Tab Controller
 * "Multimodal Biometric Attendance & Wage Auditing"
 * Isolated Block-Level Integrity & Dynamic Financial Aggregation
 */

const state = {
    activeTab: 'tab-biometric',
    workers: [],
    selectedWorkerId: 'WRK-MH-1042',
    shiftsWorked: 1.0,
    captureType: 'LIVE',
    isProcessing: false,
    ledger: {
        records: [],
        current_merkle_root: '',
        last_certified_merkle_root: '',
        total_wage: 0,
        blocked_corrupted_wage: 0,
        records_count: 0,
        verified_records_count: 0,
        tampered_records_count: 0,
        is_ledger_valid: true,
        corrupted_record_ids: [],
    },
    merkleTree: null,
    auditResult: null,
    queueLogs: [],
};

document.addEventListener('DOMContentLoaded', async () => {
    setupTabNavigation();
    setupEventListeners();
    await loadInitialData();
});

function setupTabNavigation() {
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-tab');
            switchTab(targetId);
        });
    });
}

function switchTab(targetId) {
    state.activeTab = targetId;

    document.querySelectorAll('.tab-btn').forEach(btn => {
        if (btn.getAttribute('data-tab') === targetId) {
            btn.classList.add('tab-active');
        } else {
            btn.classList.remove('tab-active');
        }
    });

    document.querySelectorAll('.tab-pane').forEach(pane => {
        if (pane.id === targetId) {
            pane.classList.remove('hidden');
        } else {
            pane.classList.add('hidden');
        }
    });

    if (targetId === 'tab-ledger') {
        renderLedgerBlocks();
        renderMerkleTreeView();
        updateLedgerSummary();
    } else if (targetId === 'tab-queue') {
        renderQueueLogs();
    }
}

function setupEventListeners() {
    document.querySelectorAll('input[name="test-mode"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            state.captureType = e.target.value;
        });
    });

    const shiftSelect = document.getElementById('shift-select');
    if (shiftSelect) {
        shiftSelect.addEventListener('change', (e) => {
            state.shiftsWorked = parseFloat(e.target.value) || 1.0;
            const shiftLabel = document.getElementById('shift-label');
            if (shiftLabel) {
                const map = {
                    '0.5': '0.5 Half-Day (4h)',
                    '1.0': '1.0 Full Shift (8h)',
                    '1.5': '1.5 Shift + OT (12h)',
                    '2.0': '2.0 Double Shift (16h)',
                };
                shiftLabel.textContent = map[e.target.value] || `${state.shiftsWorked} Shift`;
            }
        });
    }

    const punchBtn = document.getElementById('btn-punch-in');
    if (punchBtn) punchBtn.addEventListener('click', handlePunchIn);

    const applyTamperBtn = document.getElementById('btn-apply-tamper');
    if (applyTamperBtn) applyTamperBtn.addEventListener('click', handleApplyTamper);

    const auditBtn = document.getElementById('btn-run-audit');
    if (auditBtn) auditBtn.addEventListener('click', runTamperAudit);

    const resetBtn = document.getElementById('btn-reset-ledger');
    if (resetBtn) resetBtn.addEventListener('click', resetLedger);

    const topAuditBtn = document.getElementById('topbar-btn-audit');
    if (topAuditBtn) {
        topAuditBtn.addEventListener('click', () => {
            switchTab('tab-ledger');
            runTamperAudit();
        });
    }
}

async function loadInitialData() {
    try {
        await Promise.all([
            fetchWorkers(),
            fetchLedger(),
            fetchMerkleTree(),
            fetchQueueLogs(),
        ]);
        renderWorkerList();
        renderLedgerBlocks();
        renderMerkleTreeView();
        renderQueueLogs();
        updateLedgerSummary();
    } catch (err) {
        console.error('Initialization error:', err);
    }
}

// API Calls
async function fetchWorkers() {
    const res = await fetch('/api/v1/workers');
    const data = await res.json();
    state.workers = data.workers || data.employees;
}

async function fetchLedger() {
    const res = await fetch('/api/v1/ledger');
    state.ledger = await res.json();
    updateLedgerSummary();
}

async function fetchMerkleTree() {
    const res = await fetch('/api/v1/merkle-tree');
    state.merkleTree = await res.json();
}

async function fetchQueueLogs() {
    const res = await fetch('/api/v1/queue/logs?limit=25');
    const data = await res.json();
    state.queueLogs = data.logs;
}

async function refreshQueueLogs() {
    await fetchQueueLogs();
    renderQueueLogs();
}

// UI Renderers - Tab 1
function renderWorkerList() {
    const container = document.getElementById('worker-list');
    if (!container) return;

    container.innerHTML = state.workers.map(w => {
        const isSelected = w.worker_id === state.selectedWorkerId;
        return `
            <div onclick="selectWorker('${w.worker_id}')"
                 class="cursor-pointer p-2.5 rounded-lg border transition-all text-xs flex items-center justify-between ${
                     isSelected 
                         ? 'border-blue-600 bg-blue-50/70 ring-1 ring-blue-600 shadow-xs' 
                         : 'border-slate-200 bg-white hover:border-slate-300'
                 }">
                <div class="flex items-center gap-2.5">
                    <div class="w-7 h-7 rounded-full bg-slate-800 text-white flex items-center justify-center font-bold text-xs">
                        ${w.initials}
                    </div>
                    <div>
                        <div class="flex items-center gap-1.5">
                            <span class="font-bold text-slate-800">${w.name}</span>
                            <span class="text-[10px] font-mono px-1 py-0.2 rounded bg-slate-100 text-slate-600 border border-slate-200">${w.worker_id}</span>
                        </div>
                        <p class="text-[11px] text-slate-500">${w.trade}</p>
                    </div>
                </div>
                <div class="text-right">
                    <span class="font-bold text-slate-900 text-xs">₹${w.daily_wage_rate.toFixed(0)}/d</span>
                </div>
            </div>
        `;
    }).join('');

    const tamperSelect = document.getElementById('tamper-record-select');
    if (tamperSelect && state.ledger.records) {
        tamperSelect.innerHTML = state.ledger.records.map(r => `
            <option value="${r.record_id}">Record #${r.record_id}: ${r.worker_name} (${r.trade}) &bull; ${r.shifts_worked} shift = ₹${r.calculated_wage}</option>
        `).join('');
    }
}

function selectWorker(workerId) {
    state.selectedWorkerId = workerId;
    renderWorkerList();
}

async function handlePunchIn() {
    if (state.isProcessing) return;
    state.isProcessing = true;

    const punchBtn = document.getElementById('btn-punch-in');
    const originalText = punchBtn ? punchBtn.innerHTML : '';
    if (punchBtn) {
        punchBtn.disabled = true;
        punchBtn.innerHTML = `<span>Verifying & Ingesting Shift...</span>`;
    }

    try {
        const payload = {
            worker_id: state.selectedWorkerId,
            shifts_worked: state.shiftsWorked,
            capture_type: state.captureType,
        };

        const res = await fetch('/api/v1/attendance/punch-in', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
        });

        const data = await res.json();
        const bio = data.biometric_result;

        renderPunchResultNotice(bio, data.committed_record);
        renderBiometricHUDResult(bio);

        await Promise.all([
            fetchLedger(),
            fetchMerkleTree(),
            fetchQueueLogs(),
        ]);

        renderQueueLogs();
        renderLedgerBlocks();
        renderMerkleTreeView();
        updateLedgerSummary();

    } catch (err) {
        console.error('Punch in failed:', err);
    } finally {
        state.isProcessing = false;
        if (punchBtn) {
            punchBtn.disabled = false;
            punchBtn.innerHTML = originalText;
        }
    }
}

function renderPunchResultNotice(bio, record) {
    const banner = document.getElementById('punch-result-banner');
    if (!banner) return;

    banner.classList.remove('hidden');

    if (bio.is_live && record) {
        banner.className = 'p-3.5 rounded-lg border border-emerald-300 bg-emerald-50 text-xs text-emerald-900 space-y-1';
        banner.innerHTML = `
            <div class="flex items-center justify-between">
                <span class="font-bold flex items-center gap-1.5 text-emerald-800">
                    <span class="w-2 h-2 rounded-full bg-emerald-600"></span>
                    ✓ Live Worker Verified: ${record.worker_name} (${record.worker_id})
                </span>
                <span class="font-mono text-[11px] text-emerald-700 font-semibold">PAD: ${(bio.pad_score * 100).toFixed(1)}% (Pass)</span>
            </div>
            <p class="text-[11px] text-emerald-800">
                Shift Allocation: <strong>${record.shifts_worked} shift</strong> &bull; Credited: <strong>₹${record.calculated_wage.toFixed(2)}</strong> &bull; Chained to Ledger (Record #${record.record_id}).
            </p>
        `;
    } else {
        banner.className = 'p-3.5 rounded-lg border border-rose-300 bg-rose-50 text-xs text-rose-900 space-y-1';
        banner.innerHTML = `
            <div class="flex items-center justify-between">
                <span class="font-bold flex items-center gap-1.5 text-rose-800">
                    <span class="w-2 h-2 rounded-full bg-rose-600"></span>
                    ⛔ Proxy Attack Blocked: ${bio.attack_type || 'Spoof Presentation Detected'}
                </span>
                <span class="font-mono text-[11px] text-rose-700 font-semibold">PAD: ${(bio.pad_score * 100).toFixed(1)}% (&lt; 82%)</span>
            </div>
            <p class="text-[11px] text-rose-800">
                Contractor proxy punch rejected. Zero shifts credited &bull; ₹0.00 wage added &bull; Ledger append blocked.
            </p>
        `;
    }
}

function renderBiometricHUDResult(result) {
    const hudContainer = document.getElementById('biometric-hud-result');
    const badgeEl = document.getElementById('scanner-badge');
    if (!hudContainer) return;

    const isLive = result.is_live;
    if (badgeEl) {
        badgeEl.textContent = isLive ? '✓ Genuine Worker Confirmed' : '⛔ Proxy Spoof Blocked';
        badgeEl.className = `text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${isLive ? 'bg-emerald-50 text-emerald-700 border-emerald-200' : 'bg-rose-50 text-rose-700 border-rose-200'}`;
    }

    hudContainer.innerHTML = `
        <div class="overflow-x-auto">
            <table class="w-full text-xs text-left">
                <thead class="text-[11px] text-slate-500 uppercase bg-slate-50 border-b border-slate-200">
                    <tr>
                        <th class="py-2 px-2.5">Feature Metric</th>
                        <th class="py-2 px-2.5">Measured Value</th>
                        <th class="py-2 px-2.5">Threshold</th>
                        <th class="py-2 px-2.5">Result</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-100 font-mono">
                    <tr>
                        <td class="py-2 px-2.5 font-sans font-medium text-slate-800">Multi-Spectral PAD Index</td>
                        <td class="py-2 px-2.5 font-bold ${result.pad_score >= result.threshold ? 'text-emerald-700' : 'text-rose-700'}">${result.pad_score}</td>
                        <td class="py-2 px-2.5 text-slate-500">&ge; ${result.threshold}</td>
                        <td class="py-2 px-2.5 font-sans">${result.pad_score >= result.threshold ? '<span class="text-emerald-700 font-semibold">Passed</span>' : '<span class="text-rose-700 font-semibold">Rejected</span>'}</td>
                    </tr>
                    <tr>
                        <td class="py-2 px-2.5 font-sans font-medium text-slate-800">Identity Template Match</td>
                        <td class="py-2 px-2.5 text-slate-800">${result.face_match_confidence}</td>
                        <td class="py-2 px-2.5 text-slate-500">&ge; 0.70</td>
                        <td class="py-2 px-2.5 font-sans"><span class="text-emerald-700 font-semibold">Match</span></td>
                    </tr>
                    <tr>
                        <td class="py-2 px-2.5 font-sans font-medium text-slate-800">Fourier Texture Frequency</td>
                        <td class="py-2 px-2.5 text-slate-800">${result.fourier_texture_score}</td>
                        <td class="py-2 px-2.5 text-slate-500">&ge; 0.60</td>
                        <td class="py-2 px-2.5 font-sans">${result.fourier_texture_score >= 0.6 ? '<span class="text-emerald-700 font-semibold">Normal</span>' : '<span class="text-rose-700 font-semibold">Artifacts</span>'}</td>
                    </tr>
                    <tr>
                        <td class="py-2 px-2.5 font-sans font-medium text-slate-800">Stereo Depth Disparity</td>
                        <td class="py-2 px-2.5 text-slate-800">${result.depth_disparity_score}</td>
                        <td class="py-2 px-2.5 text-slate-500">&ge; 0.60</td>
                        <td class="py-2 px-2.5 font-sans">${result.depth_disparity_score >= 0.6 ? '<span class="text-emerald-700 font-semibold">3D Volume</span>' : '<span class="text-rose-700 font-semibold">Flat 2D</span>'}</td>
                    </tr>
                </tbody>
            </table>
        </div>

        <div class="mt-2.5 pt-2 border-t border-slate-100 flex flex-wrap items-center justify-between text-xs font-mono text-slate-600 gap-2">
            <div>
                <span class="text-slate-500 font-sans">Proof Token:</span>
                <span class="text-slate-900 font-semibold">${result.proof_token}</span>
            </div>
            <div class="font-sans">
                Status: <span class="font-semibold ${isLive ? 'text-emerald-700' : 'text-rose-700'}">${isLive ? 'Chained into Muster Roll' : 'Dropped by Security Sentinel'}</span>
            </div>
        </div>
    `;
}

// Tab 2: Queue Log Renderer
function renderQueueLogs() {
    const box = document.getElementById('queue-log-box');
    if (!box) return;

    if (!state.queueLogs || state.queueLogs.length === 0) {
        box.innerHTML = `<div class="text-slate-400">Waiting for shift punch activity...</div>`;
        return;
    }

    box.innerHTML = state.queueLogs.map(log => {
        let tag = '[GATEWAY]';
        let color = 'text-cyan-400';
        if (log.phase.includes('REDIS')) { tag = '[REDIS]'; color = 'text-purple-400'; }
        if (log.phase.includes('CELERY')) { tag = '[CELERY]'; color = 'text-amber-400'; }
        if (log.phase.includes('LEDGER')) { tag = '[LEDGER]'; color = 'text-emerald-400'; }
        if (log.status.includes('SPOOF') || log.status.includes('DROPPED')) { tag = '[SENTINEL]'; color = 'text-rose-400'; }

        return `
            <div class="flex items-start gap-2 py-0.5">
                <span class="text-slate-500 shrink-0">${log.timestamp}</span>
                <span class="${color} font-bold shrink-0">${tag}</span>
                <span class="text-slate-300 truncate">${log.message}</span>
                <span class="text-slate-500 text-[10px] ml-auto shrink-0">${log.latency_ms}ms</span>
            </div>
        `;
    }).join('');
}

// Tab 3: Ledger Summary & Blocks (Block-by-Block Verification!)
function updateLedgerSummary() {
    const recCount = document.getElementById('ledger-records-count');
    const totWage = document.getElementById('ledger-total-wage');
    const blockedWage = document.getElementById('ledger-blocked-wage');
    const blockedSubtext = document.getElementById('ledger-blocked-subtext');
    const statusPill = document.getElementById('ledger-status-pill');

    if (recCount) recCount.textContent = `${state.ledger.records_count} Blocks`;
    
    // Certified wage dynamically reflects ONLY genuine verified blocks!
    if (totWage) {
        totWage.textContent = `₹${state.ledger.total_wage.toFixed(2)}`;
    }

    if (blockedWage) {
        blockedWage.textContent = `₹${(state.ledger.blocked_corrupted_wage || 0).toFixed(2)}`;
        if (state.ledger.blocked_corrupted_wage > 0) {
            blockedWage.className = 'font-mono font-bold text-rose-700 text-base mt-0.5 block';
            if (blockedSubtext) blockedSubtext.textContent = '⛔ Corrupted Payout Withheld';
        } else {
            blockedWage.className = 'font-mono font-bold text-slate-500 text-base mt-0.5 block';
            if (blockedSubtext) blockedSubtext.textContent = 'Zero fraudulent wage';
        }
    }

    if (statusPill) {
        const hasTamperedBlocks = (state.ledger.tampered_records_count > 0) || 
                                  (!state.ledger.is_ledger_valid) || 
                                  (state.auditResult && !state.auditResult.is_valid);

        if (hasTamperedBlocks) {
            const count = state.ledger.tampered_records_count || (state.auditResult ? state.auditResult.tampered_records_count : 1);
            statusPill.innerHTML = `<span class="text-xs font-bold text-rose-700 bg-rose-50 px-2 py-0.5 rounded border border-rose-300">⚠️ TAMPER DETECTED (${count} Block Corrupted)</span>`;
        } else {
            statusPill.innerHTML = `<span class="text-xs font-bold text-emerald-700 bg-emerald-50 px-2 py-0.5 rounded border border-emerald-200">✓ SEALED & VALID</span>`;
        }
    }
}

function renderLedgerBlocks() {
    const container = document.getElementById('ledger-blocks-container');
    if (!container) return;

    if (!state.ledger.records || state.ledger.records.length === 0) {
        container.innerHTML = `<div class="p-4 text-center text-slate-400 text-xs">No records in ledger.</div>`;
        return;
    }

    renderWorkerList();

    const audit = state.auditResult;

    container.innerHTML = state.ledger.records.map((rec, idx) => {
        // Strictly block-by-block integrity:
        let isCorrupted = false;
        let isChainBroken = false;

        if (audit && audit.chain_details && audit.chain_details[idx]) {
            const detail = audit.chain_details[idx];
            if (detail.status === 'CORRUPTED_PAYLOAD') isCorrupted = true;
            if (detail.status === 'BROKEN_CHAIN') isChainBroken = true;
        } else {
            if (rec.is_corrupted) isCorrupted = true;
            if (rec.is_downstream_broken) isChainBroken = true;
        }

        const isBlockValid = !isCorrupted && !isChainBroken;

        let cardClass = 'border-slate-200 bg-white';
        let badge = `<span class="text-[10px] font-bold px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 border border-emerald-200">✓ VALID HASH LINK</span>`;

        if (isCorrupted) {
            cardClass = 'border-rose-400 bg-rose-50/70 ring-1 ring-rose-400';
            badge = `<span class="text-[10px] font-bold px-2 py-0.5 rounded bg-rose-100 text-rose-800 border border-rose-300 animate-pulse">💥 TAMPER DETECTED (EXCLUDED FROM WAGE)</span>`;
        } else if (isChainBroken) {
            cardClass = 'border-amber-300 bg-amber-50/40 border-dashed';
            badge = `<span class="text-[10px] font-bold px-2 py-0.5 rounded bg-amber-100 text-amber-800 border border-amber-200">⚠️ BROKEN CHAIN LINK</span>`;
        }

        return `
            <div class="relative">
                ${idx > 0 ? `
                    <div class="flex items-center justify-center -my-1 z-10 relative">
                        <div class="px-2 py-0.2 bg-white rounded-full border border-slate-200 text-[9px] font-mono ${isBlockValid ? 'text-slate-400' : 'text-rose-500 font-bold border-rose-200'}">
                            ↓ SHA-256 PREVIOUS LINK
                        </div>
                    </div>
                ` : ''}

                <div class="p-3.5 rounded-lg border ${cardClass} shadow-xs text-xs space-y-2">
                    <div class="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 pb-2">
                        <div class="flex items-center gap-2">
                            <span class="w-5 h-5 rounded ${isBlockValid ? 'bg-slate-100 text-slate-700 border-slate-200' : 'bg-rose-100 text-rose-800 border-rose-300'} border flex items-center justify-center font-mono font-bold text-[10px]">
                                #${rec.record_id}
                            </span>
                            <span class="font-bold text-slate-900">${rec.worker_name}</span>
                            <span class="text-slate-500">(${rec.trade})</span>
                        </div>
                        <div class="flex items-center gap-2">
                            ${badge}
                            <span class="font-mono text-slate-700 font-bold ${isCorrupted ? 'text-rose-700 line-through' : 'text-emerald-700'}">
                                ${rec.shifts_worked} shift = ₹${rec.calculated_wage.toFixed(2)}
                            </span>
                        </div>
                    </div>

                    <div class="font-mono text-[10px] space-y-1">
                        <div class="flex items-center gap-2 text-slate-500">
                            <span class="w-14 uppercase">Prev:</span>
                            <span class="bg-slate-50 px-1.5 py-0.5 rounded border border-slate-200 truncate flex-1">${rec.prev_hash}</span>
                        </div>
                        <div class="flex items-center gap-2 text-slate-800">
                            <span class="w-14 uppercase font-bold text-blue-700">Hash:</span>
                            <span class="px-1.5 py-0.5 rounded border ${isCorrupted ? 'bg-rose-100 border-rose-300 text-rose-900 font-bold' : 'bg-slate-50 border-slate-200 text-slate-900'} truncate flex-1 font-semibold">${rec.record_hash}</span>
                        </div>
                    </div>

                    ${isCorrupted ? `
                        <div class="bg-rose-100/60 p-2 rounded border border-rose-200 text-[11px] font-sans text-rose-800">
                            <strong>Integrity Violation:</strong> Payload data was altered in storage without cryptographic authority. This block is isolated and its ₹${rec.calculated_wage.toFixed(2)} entitlement is blocked from payout. Other genuine shifts remain valid.
                        </div>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function renderMerkleTreeView() {
    const container = document.getElementById('merkle-tree-container');
    if (!container || !state.merkleTree) return;

    const tree = state.merkleTree;
    const levels = tree.levels || [];

    if (levels.length === 0) {
        container.innerHTML = `<div class="p-4 text-center text-slate-400 text-xs">Merkle tree is empty.</div>`;
        return;
    }

    let html = `<div class="flex flex-col-reverse gap-3 items-center w-full py-1">`;

    levels.forEach((levelNodes, levelIdx) => {
        const isLeaves = levelIdx === 0;
        const isRoot = levelIdx === levels.length - 1;

        html += `
            <div class="flex flex-col items-center w-full">
                <div class="text-[10px] font-mono text-slate-400 uppercase tracking-wider mb-1">
                    ${isRoot ? '★ Certified Merkle Epoch Root' : isLeaves ? 'Leaf Hashes (Shift Hash Signatures)' : `Rollup Level ${levelIdx}`}
                </div>
                <div class="flex flex-wrap justify-center gap-2.5 w-full">
                    ${levelNodes.map(node => {
                        const isRootNode = isRoot;
                        const nodeColor = isRootNode 
                            ? 'bg-blue-50 border-blue-300 text-blue-900 font-bold' 
                            : isLeaves 
                            ? 'bg-white border-slate-200 text-slate-700' 
                            : 'bg-slate-50 border-slate-200 text-slate-700';

                        return `
                            <div class="p-2 rounded border ${nodeColor} font-mono text-center shadow-xs max-w-[210px] flex-1 min-w-[160px]">
                                <div class="text-[11px] truncate mb-0.5 font-sans font-semibold text-slate-800">
                                    ${node.label || 'Muster Node'}
                                </div>
                                <div class="text-[10px] truncate bg-white px-1 py-0.5 rounded border border-slate-200 text-slate-600" title="${node.hash}">
                                    ${node.hash.substring(0, 16)}...
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    });

    html += `</div>`;
    container.innerHTML = html;
}

// Tamper simulation
async function handleApplyTamper() {
    const recordSelect = document.getElementById('tamper-record-select');
    const shiftsInput = document.getElementById('tamper-shifts-input');

    if (!recordSelect || !shiftsInput) return;

    const recordId = parseInt(recordSelect.value);
    const forgedShifts = parseFloat(shiftsInput.value);

    try {
        await fetch('/api/v1/ledger/tamper', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                record_id: recordId,
                forged_shifts: forgedShifts,
            }),
        });

        await fetchLedger();
        await fetchMerkleTree();
        await runTamperAudit();

    } catch (err) {
        console.error('Tamper error:', err);
    }
}

async function runTamperAudit() {
    try {
        const res = await fetch('/api/v1/ledger/audit', { method: 'POST' });
        const audit = await res.json();
        state.auditResult = audit;

        await fetchLedger();

        renderLedgerBlocks();
        renderMerkleTreeView();
        updateLedgerSummary();
        renderAuditResultBanner(audit);

    } catch (err) {
        console.error('Audit error:', err);
    }
}

function renderAuditResultBanner(audit) {
    const banner = document.getElementById('audit-result-banner');
    if (!banner) return;

    banner.classList.remove('hidden');

    if (audit.is_valid) {
        banner.className = 'p-4 rounded-lg border border-emerald-300 bg-emerald-50 text-xs text-emerald-900 space-y-1';
        banner.innerHTML = `
            <div class="font-bold flex items-center justify-between">
                <span class="flex items-center gap-1.5 text-emerald-800">
                    <span>✓</span>
                    Muster Audit Passed: 100% Cryptographic Continuity Verified
                </span>
                <span class="text-[10px] bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded font-mono font-bold">ALL PAYOUTS AUTHORIZED</span>
            </div>
            <p class="text-[11px] text-emerald-800">
                All ${audit.total_records_count} shift block hashes match canonical payloads. Total certified wage entitlement: <strong>₹${audit.total_audited_wage.toFixed(2)}</strong>.
            </p>
        `;
    } else {
        const corruptedId = audit.broken_record_id || (audit.corrupted_record_ids && audit.corrupted_record_ids[0]);
        banner.className = 'p-4 rounded-lg border border-rose-300 bg-rose-50 text-xs text-rose-900 space-y-2';
        banner.innerHTML = `
            <div class="font-bold flex items-center justify-between text-rose-800">
                <span class="flex items-center gap-1.5">
                    <span>🚨</span>
                    Tampering Isolated to Shift Block #${corruptedId}!
                </span>
                <span class="text-[10px] bg-rose-200 text-rose-900 px-2 py-0.5 rounded font-mono font-bold">FRAUDULENT WAGE BLOCKED</span>
            </div>
            <p class="text-[11px] text-rose-800">
                Payload data altered in storage without cryptographic authority. Block #${corruptedId} is excluded from payout. All other genuine worker blocks remain certified.
            </p>
            <div class="bg-white p-2.5 rounded border border-rose-200 font-mono text-[10px] space-y-1">
                <div>Original Block Hash: &nbsp;<span class="text-slate-700">${audit.stored_hash}</span></div>
                <div>Recomputed from Data: <span class="text-rose-700 font-bold">${audit.recomputed_hash}</span></div>
            </div>
            <div class="p-2 rounded bg-rose-100/70 border border-rose-200 text-[11px] font-sans text-rose-900 flex justify-between items-center">
                <span><strong>Financial Protection:</strong> ₹${audit.blocked_corrupted_wage.toFixed(2)} withheld from payout. Genuine shifts certified: ₹${audit.total_audited_wage.toFixed(2)}.</span>
                <span class="font-mono font-bold text-rose-800">${audit.verified_records_count}/${audit.total_records_count} Blocks Valid</span>
            </div>
        `;
    }
}

async function resetLedger() {
    try {
        await fetch('/api/v1/ledger/reset', { method: 'POST' });
        state.auditResult = null;
        const banner = document.getElementById('audit-result-banner');
        if (banner) banner.classList.add('hidden');

        await Promise.all([
            fetchLedger(),
            fetchMerkleTree(),
            fetchQueueLogs(),
        ]);

        renderLedgerBlocks();
        renderMerkleTreeView();
        updateLedgerSummary();

    } catch (err) {
        console.error('Reset error:', err);
    }
}

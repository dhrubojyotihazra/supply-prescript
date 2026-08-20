import React, { useState, useEffect, useCallback } from 'react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://127.0.0.1:8000'
  : '';

// ─── Workflow Step Tracker ────────────────────────────────────────────────────
const STEPS = [
  { id: 1, label: 'Identify', icon: '🔍', desc: 'Surface high-risk warehouse from the priority queue' },
  { id: 2, label: 'Analyze', icon: '🧠', desc: 'Review warehouse risk factors and XGBoost signals' },
  { id: 3, label: 'Prescribe', icon: '⚡', desc: 'Run SciPy linprog optimizer for allocation choices' },
  { id: 4, label: 'Justify', icon: '✍️', desc: 'Write your analyst reasoning before executing' },
  { id: 5, label: 'Execute', icon: '✅', desc: 'Write-back decision to PostgreSQL database' },
  { id: 6, label: 'Evaluate', icon: '📊', desc: 'Log actual outcome to close the feedback loop' },
];

function WorkflowStepper({ activeStep }) {
  return (
    <div style={{ display: 'flex', gap: 0, marginBottom: '1.5rem', overflowX: 'auto' }}>
      {STEPS.map((step, i) => {
        const done = step.id < activeStep;
        const active = step.id === activeStep;
        return (
          <div key={step.id} style={{ display: 'flex', alignItems: 'center', flex: 1, minWidth: 0 }}>
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '0.3rem',
              flex: 1,
              minWidth: 0,
            }}>
              <div style={{
                width: 40, height: 40,
                borderRadius: '8px',
                border: '3px solid #000',
                background: done ? '#4ade80' : active ? '#facc15' : '#fff',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: done ? '1rem' : '1.1rem',
                fontWeight: 900,
                boxShadow: active ? '3px 3px 0px #000' : '2px 2px 0px #000',
                flexShrink: 0,
              }}>
                {done ? '✓' : step.icon}
              </div>
              <div style={{
                fontSize: '0.65rem', fontWeight: 900, textTransform: 'uppercase',
                color: active ? '#000' : done ? '#16a34a' : '#6b7280',
                textAlign: 'center', letterSpacing: '0.04em',
              }}>
                {step.label}
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{
                height: 3, flex: 1, minWidth: 12,
                background: done ? '#4ade80' : '#e5e7eb',
                border: done ? '1px solid #16a34a' : '1px solid #d1d5db',
                margin: '0 0.15rem',
                marginBottom: '1.5rem',
              }} />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ─── Priority Badge ────────────────────────────────────────────────────────────
function PriorityBadge({ priority }) {
  const colors = {
    CRITICAL: { bg: '#ff4757', text: '#fff' },
    HIGH: { bg: '#fbbf24', text: '#000' },
    MEDIUM: { bg: '#38bdf8', text: '#000' },
    LOW: { bg: '#e5e7eb', text: '#000' },
  };
  const c = colors[priority] || colors.LOW;
  return (
    <span style={{
      background: c.bg, color: c.text,
      border: '2px solid #000', borderRadius: '6px',
      padding: '0.15rem 0.55rem',
      fontWeight: 900, fontSize: '0.7rem',
      boxShadow: '2px 2px 0px #000',
      textTransform: 'uppercase',
    }}>
      {priority}
    </span>
  );
}

// ─── Risk Score Ring ──────────────────────────────────────────────────────────
function RiskRing({ score }) {
  const max = 150;
  const pct = Math.min(score / max, 1);
  const color = score >= 80 ? '#ff4757' : score >= 50 ? '#fbbf24' : score >= 20 ? '#38bdf8' : '#4ade80';
  return (
    <div style={{
      position: 'relative', width: 72, height: 72, flexShrink: 0,
    }}>
      <svg width="72" height="72" viewBox="0 0 72 72">
        <circle cx="36" cy="36" r="28" fill="none" stroke="#e5e7eb" strokeWidth="8" />
        <circle
          cx="36" cy="36" r="28" fill="none" stroke={color} strokeWidth="8"
          strokeDasharray={`${2 * Math.PI * 28 * pct} ${2 * Math.PI * 28 * (1 - pct)}`}
          strokeLinecap="round"
          transform="rotate(-90 36 36)"
          style={{ transition: 'stroke-dasharray 0.6s ease' }}
        />
      </svg>
      <div style={{
        position: 'absolute', inset: 0, display: 'flex',
        flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
      }}>
        <div style={{ fontSize: '1rem', fontWeight: 900, color: '#000', lineHeight: 1 }}>{score}</div>
        <div style={{ fontSize: '0.55rem', fontWeight: 800, color: '#6b7280', textTransform: 'uppercase' }}>Risk</div>
      </div>
    </div>
  );
}

// ─── Main Analyst Workspace ───────────────────────────────────────────────────
export default function AnalystWorkspaceTab({ onSelectWarehouse }) {
  const [queueData, setQueueData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [selectedWH, setSelectedWH] = useState(null);
  const [step, setStep] = useState(1);
  const [prescriptions, setPrescriptions] = useState([]);
  const [prescLoading, setPrescLoading] = useState(false);
  const [analystNotes, setAnalystNotes] = useState('');
  const [selectedChoice, setSelectedChoice] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [executedDecision, setExecutedDecision] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchQueue = useCallback(() => {
    setLoading(true);
    fetch(`${API_BASE}/analyst-queue?limit=10`)
      .then(r => r.json())
      .then(d => {
        setQueueData(d);
        setLoading(false);
        setLastRefreshed(new Date().toLocaleTimeString());
      })
      .catch(() => setLoading(false));
  }, []);

  useEffect(() => { fetchQueue(); }, [fetchQueue]);

  const handleSelectWarehouse = (wh) => {
    setSelectedWH(wh);
    setStep(2);
    setAnalystNotes('');
    setSelectedChoice(null);
    setPrescriptions([]);
    setExecutedDecision(null);
  };

  const handleRunPrescriptions = () => {
    if (!selectedWH) return;
    setStep(3);
    setPrescLoading(true);
    fetch(`${API_BASE}/prescribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        warehouse_id: selectedWH.warehouse_id,
        dist_from_hub: selectedWH.dist_from_hub,
        product_wg_ton: selectedWH.product_wg_ton,
        capacity_size: selectedWH.capacity_size,
      }),
    })
      .then(r => r.json())
      .then(d => {
        setPrescriptions(d.choices || []);
        setPrescLoading(false);
      })
      .catch(() => setPrescLoading(false));
  };

  const handleSelectChoice = (choice) => {
    setSelectedChoice(choice);
    setStep(4);
  };

  const handleExecute = async () => {
    if (!selectedWH || !selectedChoice || !analystNotes.trim()) return;
    setExecuting(true);
    try {
      const res = await fetch(`${API_BASE}/execute-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          warehouse_id: selectedWH.warehouse_id,
          selected_option: selectedChoice.label,
          prescribed_cost: selectedChoice.total_cost,
          expected_delay_days: selectedChoice.expected_delay_days || 5,
          analyst_notes: analystNotes.trim(),
        }),
      });
      const data = await res.json();
      setExecuting(false);
      if (res.ok) {
        setExecutedDecision(data);
        setStep(5);
      }
    } catch {
      setExecuting(false);
    }
  };

  const handleReset = () => {
    setSelectedWH(null);
    setStep(1);
    setAnalystNotes('');
    setSelectedChoice(null);
    setPrescriptions([]);
    setExecutedDecision(null);
    fetchQueue();
  };

  const notesValid = analystNotes.trim().length >= 10;

  return (
    <div style={{ width: '100%' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div>
          <h2 style={{ fontSize: '1.6rem', fontWeight: 900, color: '#000', textTransform: 'uppercase', letterSpacing: '-0.02em' }}>
            Analyst Workspace
          </h2>
          <p style={{ color: '#4b5563', fontWeight: 700, fontSize: '0.9rem', marginTop: '0.25rem' }}>
            You are an active participant in the AI-driven supply chain workflow — not just an observer.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {lastRefreshed && <span style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: 700 }}>Queue refreshed: {lastRefreshed}</span>}
          <button className="btn-secondary" onClick={handleReset} style={{ fontWeight: 900 }}>↺ Reset Workspace</button>
        </div>
      </div>

      {/* Workflow Stepper */}
      <div style={{ background: '#fff', border: '3px solid #000', borderRadius: '8px', boxShadow: '4px 4px 0px #000', padding: '1.25rem 1.5rem', marginBottom: '1.5rem' }}>
        <div style={{ fontSize: '0.75rem', fontWeight: 900, textTransform: 'uppercase', color: '#6b7280', marginBottom: '1rem', letterSpacing: '0.05em' }}>
          Guided Analyst Workflow — Step {step} of {STEPS.length}: {STEPS[step - 1]?.desc}
        </div>
        <WorkflowStepper activeStep={step} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', alignItems: 'start' }}>

        {/* LEFT PANEL: Priority Queue */}
        <div>
          <div style={{ background: '#fff', border: '3px solid #000', borderRadius: '8px', boxShadow: '4px 4px 0px #000' }}>
            <div style={{
              padding: '1rem 1.25rem', borderBottom: '3px solid #000',
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
            }}>
              <div>
                <h3 style={{ fontWeight: 900, fontSize: '0.95rem', textTransform: 'uppercase', color: '#000' }}>
                  AI Priority Queue
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#4b5563', fontWeight: 700, marginTop: '0.1rem' }}>
                  Ranked by composite risk score — act on these first
                </p>
              </div>
              {queueData?.pending_outcome_count > 0 && (
                <div style={{
                  background: '#fce7f3', border: '2px solid #db2777',
                  borderRadius: '6px', padding: '0.4rem 0.75rem',
                  fontWeight: 900, fontSize: '0.75rem', color: '#9d174d',
                  boxShadow: '2px 2px 0px #db2777',
                }}>
                  {queueData.pending_outcome_count} outcome{queueData.pending_outcome_count > 1 ? 's' : ''} awaiting eval →
                </div>
              )}
            </div>

            {loading ? (
              <div style={{ padding: '2rem', textAlign: 'center', fontWeight: 800, color: '#000' }}>
                Loading AI priority queue...
              </div>
            ) : (
              <div style={{ padding: '0.75rem', display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                {(queueData?.priority_queue || []).map((wh) => (
                  <div
                    key={wh.warehouse_id}
                    onClick={() => handleSelectWarehouse(wh)}
                    style={{
                      display: 'flex', alignItems: 'center', gap: '0.85rem',
                      background: selectedWH?.warehouse_id === wh.warehouse_id ? '#fef9c3' : '#f8fafc',
                      border: selectedWH?.warehouse_id === wh.warehouse_id ? '3px solid #000' : '2px solid #000',
                      borderRadius: '8px', padding: '0.75rem',
                      cursor: 'pointer', transition: 'all 0.15s ease',
                      boxShadow: selectedWH?.warehouse_id === wh.warehouse_id ? '3px 3px 0px #000' : '2px 2px 0px #000',
                    }}
                    onMouseEnter={e => { e.currentTarget.style.transform = 'translate(-1px,-1px)'; e.currentTarget.style.boxShadow = '3px 3px 0px #000'; }}
                    onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = selectedWH?.warehouse_id === wh.warehouse_id ? '3px 3px 0px #000' : '2px 2px 0px #000'; }}
                  >
                    <RiskRing score={wh.risk_score} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.25rem' }}>
                        <span style={{ fontWeight: 900, fontSize: '0.9rem', color: '#000' }}>{wh.warehouse_id}</span>
                        <PriorityBadge priority={wh.priority} />
                      </div>
                      <div style={{ fontSize: '0.75rem', color: '#4b5563', fontWeight: 700 }}>
                        {wh.zone} Zone • {wh.location_type} • {wh.capacity_size} Cap
                      </div>
                      <div style={{ fontSize: '0.72rem', color: '#6b7280', fontWeight: 700, marginTop: '0.2rem' }}>
                        Issues L1Y: {wh.transport_issue_l1y} &nbsp;|&nbsp; Breakdowns: {wh.wh_breakdown_l3m} &nbsp;|&nbsp; {wh.dist_from_hub}km
                      </div>
                    </div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 900, color: '#000', textAlign: 'right' }}>
                      {wh.status === 'Delayed'
                        ? <span style={{ color: '#dc2626' }}>⚠ Delayed</span>
                        : <span style={{ color: '#16a34a' }}>✓ Normal</span>}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Pending Outcomes Nudge */}
          {queueData?.pending_outcomes?.length > 0 && (
            <div style={{
              marginTop: '1rem', background: '#fef9c3',
              border: '3px solid #000', borderRadius: '8px', boxShadow: '4px 4px 0px #000',
              padding: '1rem 1.25rem',
            }}>
              <div style={{ fontWeight: 900, fontSize: '0.85rem', color: '#000', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                Pending Outcome Evaluations
              </div>
              <p style={{ fontSize: '0.8rem', fontWeight: 700, color: '#4b5563', marginBottom: '0.75rem' }}>
                These decisions are awaiting real-world outcome logging to close the loop:
              </p>
              {queueData.pending_outcomes.map(pd => (
                <div key={pd.decision_id} style={{
                  display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  background: '#fff', border: '2px solid #000', borderRadius: '6px',
                  padding: '0.5rem 0.75rem', marginBottom: '0.4rem',
                  boxShadow: '2px 2px 0px #000', fontSize: '0.8rem', fontWeight: 800,
                }}>
                  <span>#{pd.decision_id} — {pd.warehouse_id}</span>
                  <span style={{ color: '#059669' }}>{pd.selected_option} · ${Number(pd.prescribed_cost).toLocaleString()}</span>
                </div>
              ))}
              <p style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: 700, marginTop: '0.5rem' }}>
                → Go to the <strong>Closed-Loop Outcomes</strong> tab to log actuals.
              </p>
            </div>
          )}
        </div>

        {/* RIGHT PANEL: Guided Action Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>

          {/* Step 1: Nothing selected */}
          {step === 1 && (
            <div style={{
              background: '#fff', border: '3px dashed #9ca3af', borderRadius: '8px',
              padding: '3rem 2rem', textAlign: 'center',
              display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '1rem',
            }}>
              <div style={{ fontSize: '3rem' }}>🔍</div>
              <h3 style={{ fontWeight: 900, fontSize: '1.1rem', color: '#000', textTransform: 'uppercase' }}>
                Select a Warehouse to Begin
              </h3>
              <p style={{ color: '#6b7280', fontWeight: 700, fontSize: '0.85rem', maxWidth: '280px', lineHeight: 1.6 }}>
                Click any warehouse in the Priority Queue on the left to start your guided decision workflow.
              </p>
            </div>
          )}

          {/* Step 2: Analyze selected warehouse */}
          {step >= 2 && selectedWH && (
            <div style={{ background: '#fff', border: '3px solid #000', borderRadius: '8px', boxShadow: '4px 4px 0px #000' }}>
              <div style={{
                padding: '0.85rem 1.25rem', borderBottom: '3px solid #000',
                background: '#bae6fd', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
                <div>
                  <h3 style={{ fontWeight: 900, fontSize: '0.95rem', textTransform: 'uppercase', color: '#000' }}>
                    Step 2: Analyze — {selectedWH.warehouse_id}
                  </h3>
                </div>
                <PriorityBadge priority={selectedWH.priority} />
              </div>
              <div style={{ padding: '1.25rem' }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', marginBottom: '1rem' }}>
                  {[
                    ['Zone', selectedWH.zone],
                    ['Location Type', selectedWH.location_type],
                    ['Capacity', selectedWH.capacity_size],
                    ['Workers', selectedWH.workers_num],
                    ['Distance from Hub', `${selectedWH.dist_from_hub} km`],
                    ['Product Weight', `${selectedWH.product_wg_ton} tons`],
                    ['Transport Issues (L1Y)', selectedWH.transport_issue_l1y],
                    ['Breakdowns (L3M)', selectedWH.wh_breakdown_l3m],
                  ].map(([label, value]) => (
                    <div key={label} style={{
                      background: '#f8fafc', border: '2px solid #000', borderRadius: '6px',
                      padding: '0.5rem 0.65rem', boxShadow: '1px 1px 0px #000',
                    }}>
                      <div style={{ fontSize: '0.65rem', fontWeight: 900, textTransform: 'uppercase', color: '#6b7280', marginBottom: '0.15rem' }}>{label}</div>
                      <div style={{ fontSize: '0.9rem', fontWeight: 900, color: '#000' }}>{value ?? 'N/A'}</div>
                    </div>
                  ))}
                </div>

                {/* AI Risk Signal */}
                <div style={{
                  background: selectedWH.risk_score >= 80 ? '#ffe4e6' : selectedWH.risk_score >= 50 ? '#fef9c3' : '#f0fdf4',
                  border: '2px solid #000', borderRadius: '6px', padding: '0.75rem',
                  boxShadow: '2px 2px 0px #000', marginBottom: '1rem',
                  display: 'flex', alignItems: 'center', gap: '0.75rem',
                }}>
                  <div style={{ fontSize: '1.5rem' }}>
                    {selectedWH.risk_score >= 80 ? '🔴' : selectedWH.risk_score >= 50 ? '🟡' : '🟢'}
                  </div>
                  <div>
                    <div style={{ fontWeight: 900, fontSize: '0.85rem', color: '#000' }}>
                      Risk Score: {selectedWH.risk_score} / 150 — {selectedWH.priority} Priority
                    </div>
                    <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#4b5563', marginTop: '0.15rem' }}>
                      {selectedWH.risk_score >= 80
                        ? 'CRITICAL: Immediate prescriptive action required. High likelihood of supply disruption.'
                        : selectedWH.risk_score >= 50
                          ? 'HIGH: Significant delay risk factors. Optimize allocation before further degradation.'
                          : 'MEDIUM/LOW: Monitor closely. Run optimizer to confirm cost-efficient routing.'}
                    </div>
                  </div>
                </div>

                {step === 2 && (
                  <button className="btn-execute" style={{ width: '100%' }} onClick={handleRunPrescriptions}>
                    ⚡ Run SciPy Optimizer → Get Allocation Choices
                  </button>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Show Prescriptions */}
          {step >= 3 && (
            <div style={{ background: '#fff', border: '3px solid #000', borderRadius: '8px', boxShadow: '4px 4px 0px #000' }}>
              <div style={{ padding: '0.85rem 1.25rem', borderBottom: '3px solid #000', background: '#fef08a' }}>
                <h3 style={{ fontWeight: 900, fontSize: '0.95rem', textTransform: 'uppercase', color: '#000' }}>
                  Step 3: Prescribe — SciPy linprog Results
                </h3>
              </div>
              <div style={{ padding: '1rem' }}>
                {prescLoading ? (
                  <div style={{ textAlign: 'center', padding: '1.5rem', fontWeight: 800, color: '#000' }}>
                    Solving linear program...
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
                    {prescriptions.map((choice, idx) => {
                      const isSelected = selectedChoice?.label === choice.label;
                      return (
                        <div
                          key={idx}
                          onClick={() => step <= 4 && handleSelectChoice(choice)}
                          style={{
                            background: isSelected ? '#bbf7d0' : '#f8fafc',
                            border: isSelected ? '3px solid #16a34a' : '2px solid #000',
                            borderRadius: '8px', padding: '0.85rem 1rem',
                            cursor: step <= 4 ? 'pointer' : 'default',
                            boxShadow: isSelected ? '3px 3px 0px #16a34a' : '2px 2px 0px #000',
                            transition: 'all 0.15s ease',
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                            <span style={{ fontWeight: 900, fontSize: '0.9rem', color: '#000' }}>{choice.label}</span>
                            <span style={{
                              background: idx === 0 ? '#bae6fd' : idx === 1 ? '#bbf7d0' : '#f3e8ff',
                              border: '2px solid #000', borderRadius: '6px',
                              padding: '0.15rem 0.5rem', fontSize: '0.7rem', fontWeight: 900,
                              boxShadow: '1px 1px 0px #000',
                            }}>
                              Est. {choice.expected_delay_days}d delay
                            </span>
                          </div>
                          <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', fontWeight: 800, color: '#000' }}>
                            <span>Budget: ${choice.budget_limit?.toLocaleString()}</span>
                            <span style={{ color: '#059669' }}>Cost: ${choice.total_cost?.toLocaleString()}</span>
                          </div>
                          {isSelected && (
                            <div style={{ marginTop: '0.4rem', fontSize: '0.75rem', fontWeight: 900, color: '#16a34a' }}>
                              ✓ Selected — proceed to justify your reasoning below
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Analyst Justification */}
          {step >= 4 && selectedChoice && (
            <div style={{ background: '#fff', border: '3px solid #000', borderRadius: '8px', boxShadow: '4px 4px 0px #000' }}>
              <div style={{ padding: '0.85rem 1.25rem', borderBottom: '3px solid #000', background: '#fce7f3' }}>
                <h3 style={{ fontWeight: 900, fontSize: '0.95rem', textTransform: 'uppercase', color: '#000' }}>
                  Step 4: Justify Your Decision
                </h3>
                <p style={{ fontSize: '0.75rem', color: '#4b5563', fontWeight: 700, marginTop: '0.2rem' }}>
                  As the analyst, explain WHY you're choosing {selectedChoice.label}. This is stored with the decision.
                </p>
              </div>
              <div style={{ padding: '1.25rem' }}>
                <div style={{
                  background: '#f8fafc', border: '2px solid #000', borderRadius: '6px',
                  padding: '0.75rem', marginBottom: '1rem', boxShadow: '2px 2px 0px #000',
                }}>
                  <div style={{ fontSize: '0.72rem', fontWeight: 900, textTransform: 'uppercase', color: '#6b7280', marginBottom: '0.3rem' }}>
                    Selected: {selectedChoice.label} · ${selectedChoice.total_cost?.toLocaleString()} · {selectedChoice.expected_delay_days}d
                  </div>
                </div>

                <label style={{ display: 'block', fontWeight: 900, fontSize: '0.85rem', color: '#000', textTransform: 'uppercase', marginBottom: '0.5rem' }}>
                  Analyst Notes & Reasoning (min. 10 characters)
                </label>
                <textarea
                  rows={4}
                  style={{
                    width: '100%', background: '#fff', border: '3px solid #000',
                    borderRadius: '6px', padding: '0.75rem', fontSize: '0.85rem',
                    fontWeight: 700, fontFamily: 'inherit', resize: 'vertical',
                    boxShadow: '2px 2px 0px #000', outline: 'none',
                    boxSizing: 'border-box',
                  }}
                  placeholder="e.g. Choosing Choice B as it balances cost within our Q3 budget cap while minimising delay risk for this high-breakdown zone..."
                  value={analystNotes}
                  onChange={e => setAnalystNotes(e.target.value)}
                />
                <div style={{ fontSize: '0.72rem', fontWeight: 700, color: notesValid ? '#16a34a' : '#dc2626', marginTop: '0.35rem', marginBottom: '1rem' }}>
                  {notesValid ? '✓ Reasoning looks good — ready to execute' : `${Math.max(0, 10 - analystNotes.trim().length)} more characters needed`}
                </div>

                <button
                  className="btn-execute"
                  style={{
                    width: '100%',
                    opacity: (!notesValid || executing) ? 0.5 : 1,
                    cursor: (!notesValid || executing) ? 'not-allowed' : 'pointer',
                  }}
                  disabled={!notesValid || executing}
                  onClick={handleExecute}
                >
                  {executing ? 'Writing to PostgreSQL...' : `✅ Execute & Write-Back: ${selectedChoice.label} for ${selectedWH?.warehouse_id}`}
                </button>
              </div>
            </div>
          )}

          {/* Step 5: Success + Next Action */}
          {step === 5 && executedDecision && (
            <div style={{
              background: '#f0fdf4', border: '3px solid #16a34a', borderRadius: '8px',
              boxShadow: '4px 4px 0px #16a34a', padding: '1.5rem',
              display: 'flex', flexDirection: 'column', gap: '1rem',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                <div style={{ fontSize: '2rem' }}>✅</div>
                <div>
                  <h3 style={{ fontWeight: 900, fontSize: '1rem', color: '#000', textTransform: 'uppercase' }}>
                    Decision Executed Successfully
                  </h3>
                  <p style={{ fontSize: '0.8rem', fontWeight: 700, color: '#4b5563', marginTop: '0.2rem' }}>
                    Decision #{executedDecision.id} written to PostgreSQL. Loop step 5 of 6 complete.
                  </p>
                </div>
              </div>

              <div style={{
                background: '#fff', border: '2px solid #000', borderRadius: '6px',
                padding: '0.85rem', boxShadow: '2px 2px 0px #000',
              }}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.82rem', fontWeight: 800, color: '#000' }}>
                  <div>Decision ID: <strong>#{executedDecision.id}</strong></div>
                  <div>Option: <strong>{executedDecision.selected_option}</strong></div>
                  <div>Warehouse: <strong>{executedDecision.warehouse_id}</strong></div>
                  <div>Cost: <strong>${Number(executedDecision.prescribed_cost).toLocaleString()}</strong></div>
                  <div style={{ gridColumn: '1 / -1' }}>Your Notes: <em style={{ fontWeight: 700, color: '#4b5563' }}>"{executedDecision.analyst_notes}"</em></div>
                </div>
              </div>

              <div style={{
                background: '#fef9c3', border: '2px solid #000', borderRadius: '6px',
                padding: '0.85rem', boxShadow: '2px 2px 0px #000',
              }}>
                <div style={{ fontWeight: 900, fontSize: '0.85rem', color: '#000', textTransform: 'uppercase', marginBottom: '0.35rem' }}>
                  Step 6: Close the Loop →
                </div>
                <p style={{ fontSize: '0.8rem', fontWeight: 700, color: '#4b5563', lineHeight: 1.6 }}>
                  After the shipment completes, go to the <strong>Closed-Loop Outcomes</strong> tab and log the actual cost and delay for Decision #{executedDecision.id} to compound the system's business intelligence.
                </p>
              </div>

              <button className="btn-secondary" onClick={handleReset} style={{ fontWeight: 900 }}>
                ↺ Start Next Decision Workflow
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

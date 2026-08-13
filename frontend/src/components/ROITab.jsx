import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://supply-prescript-api.onrender.com';

function RoiKpiCard({ label, value, sub, color }) {
  return (
    <div style={{
      background: color,
      border: '3px solid #000',
      borderRadius: '8px',
      boxShadow: '4px 4px 0px #000',
      padding: '1rem 1.25rem',
      display: 'flex',
      flexDirection: 'column',
      gap: '0.2rem',
    }}>
      <div style={{ fontSize: '0.68rem', fontWeight: 900, textTransform: 'uppercase', letterSpacing: '0.05em', color: '#000' }}>
        {label}
      </div>
      <div style={{ fontSize: '2rem', fontWeight: 900, color: '#000', lineHeight: 1.1 }}>
        {value}
      </div>
      {sub && (
        <div style={{ fontSize: '0.72rem', fontWeight: 700, color: '#1a1a1a' }}>{sub}</div>
      )}
    </div>
  );
}

function ProgressBar({ label, value, max, color, sub }) {
  const pct = max > 0 ? Math.min((value / max) * 100, 100) : 0;
  return (
    <div style={{ marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem' }}>
        <span style={{ fontWeight: 900, fontSize: '0.85rem', color: '#000' }}>{label}</span>
        <span style={{ fontWeight: 900, fontSize: '0.85rem', color: '#000' }}>{sub}</span>
      </div>
      <div style={{
        height: '20px',
        background: '#e5e7eb',
        borderRadius: '6px',
        border: '2px solid #000',
        overflow: 'hidden',
        boxShadow: '2px 2px 0px #000',
      }}>
        <div style={{
          height: '100%',
          width: `${pct}%`,
          background: color,
          borderRadius: '4px',
          transition: 'width 0.8s cubic-bezier(0.4,0,0.2,1)',
        }} />
      </div>
    </div>
  );
}

function EmptyState() {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: '4rem 2rem',
      background: '#fff',
      border: '3px solid #000',
      borderRadius: '8px',
      boxShadow: '4px 4px 0px #000',
      textAlign: 'center',
      gap: '1rem',
    }}>
      <div style={{ fontSize: '3.5rem' }}>📊</div>
      <h2 style={{ fontWeight: 900, fontSize: '1.4rem', color: '#000', textTransform: 'uppercase' }}>
        No ROI Data Yet
      </h2>
      <p style={{ color: '#4b5563', fontWeight: 700, maxWidth: '420px', lineHeight: 1.5 }}>
        ROI analytics populate once decisions have been executed <strong>AND</strong> actual outcomes
        have been logged via the <strong>Closed-Loop Outcomes</strong> tab.
      </p>
      <div style={{
        background: '#fef9c3',
        border: '3px solid #000',
        borderRadius: '8px',
        boxShadow: '3px 3px 0px #000',
        padding: '1rem 1.5rem',
        fontWeight: 800,
        fontSize: '0.85rem',
        color: '#000',
      }}>
        Step 1: Execute a decision on any warehouse row →<br />
        Step 2: Log the actual outcome in Closed-Loop Outcomes →<br />
        Step 3: Come back here to see ROI analytics!
      </div>
    </div>
  );
}

export default function ROITab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [lastRefreshed, setLastRefreshed] = useState(null);

  const fetchROI = () => {
    setLoading(true);
    setError(null);
    fetch(`${API_BASE}/roi-analytics`)
      .then(res => res.json())
      .then(d => {
        setData(d);
        setLoading(false);
        setLastRefreshed(new Date().toLocaleTimeString());
      })
      .catch(err => {
        setError('Failed to load ROI analytics. Is the backend running?');
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchROI();
  }, []);

  const isEmpty = !data || data.total_decisions === 0;
  const noOutcomes = data && data.evaluated_outcomes === 0;

  const roiPct = data && data.total_prescribed_cost > 0
    ? ((data.total_cost_savings / data.total_prescribed_cost) * 100).toFixed(1)
    : 0;

  return (
    <div style={{ width: '100%' }}>

      {/* Page Header */}
      <div style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'flex-start',
        marginBottom: '1.5rem',
        flexWrap: 'wrap',
        gap: '0.75rem',
      }}>
        <div>
          <h2 style={{ fontSize: '1.6rem', fontWeight: 900, color: '#000', textTransform: 'uppercase', letterSpacing: '-0.02em' }}>
            Decision ROI Analytics
          </h2>
          <p style={{ color: '#4b5563', fontWeight: 700, fontSize: '0.9rem', marginTop: '0.25rem' }}>
            Tracking how often the AI recommendations resulted in positive business outcomes
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          {lastRefreshed && (
            <span style={{ fontSize: '0.75rem', color: '#6b7280', fontWeight: 700 }}>
              Refreshed: {lastRefreshed}
            </span>
          )}
          <button
            className="btn-secondary"
            onClick={fetchROI}
            disabled={loading}
            style={{ fontWeight: 900 }}
          >
            {loading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
      </div>

      {error && (
        <div style={{
          background: '#ffe4e6', border: '3px solid #f43f5e', borderRadius: '8px',
          padding: '1rem', fontWeight: 800, color: '#be123c', marginBottom: '1.5rem',
          boxShadow: '3px 3px 0px #f43f5e'
        }}>
          {error}
        </div>
      )}

      {loading && (
        <div style={{
          textAlign: 'center', padding: '3rem', fontWeight: 900, fontSize: '1.1rem',
          color: '#000', border: '3px solid #000', borderRadius: '8px',
          background: '#fff', boxShadow: '4px 4px 0px #000',
        }}>
          Loading ROI Analytics...
        </div>
      )}

      {!loading && isEmpty && <EmptyState />}

      {!loading && !isEmpty && (
        <>
          {/* ROI KPI Strip */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(175px, 1fr))',
            gap: '0.85rem',
            marginBottom: '1.5rem',
          }}>
            <RoiKpiCard
              label="Total Decisions Made"
              value={data.total_decisions}
              sub="Prescriptive actions executed"
              color="#bae6fd"
            />
            <RoiKpiCard
              label="Outcomes Evaluated"
              value={data.evaluated_outcomes}
              sub={`${data.total_decisions - data.evaluated_outcomes} pending evaluation`}
              color="#fef08a"
            />
            <RoiKpiCard
              label="Positive Outcomes"
              value={data.positive_outcomes}
              sub={`${data.positive_outcome_rate}% success rate`}
              color="#bbf7d0"
            />
            <RoiKpiCard
              label="Total Cost Savings"
              value={`$${Number(data.total_cost_savings).toLocaleString()}`}
              sub={`${roiPct}% under prescribed budget`}
              color={data.total_cost_savings >= 0 ? '#d1fae5' : '#ffe4e6'}
            />
            <RoiKpiCard
              label="Avg Delay Improvement"
              value={`${data.avg_delay_improvement >= 0 ? '-' : '+'}${Math.abs(data.avg_delay_improvement)} days`}
              sub={`Prescribed: ${data.avg_prescribed_delay}d → Actual: ${data.avg_actual_delay}d`}
              color={data.avg_delay_improvement >= 0 ? '#fce7f3' : '#ffe4e6'}
            />
          </div>

          {/* Two-column layout */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.25rem', marginBottom: '1.5rem' }}>

            {/* Option Performance */}
            <div style={{
              background: '#fff',
              border: '3px solid #000',
              borderRadius: '8px',
              boxShadow: '4px 4px 0px #000',
              padding: '1.5rem',
            }}>
              <h3 style={{ fontWeight: 900, fontSize: '1rem', color: '#000', textTransform: 'uppercase', marginBottom: '1.25rem', letterSpacing: '0.03em' }}>
                Option Success Rate
              </h3>
              {noOutcomes ? (
                <p style={{ color: '#6b7280', fontWeight: 700, fontSize: '0.85rem' }}>
                  No evaluated outcomes yet. Log outcomes to see option-level performance.
                </p>
              ) : data.option_breakdown.length === 0 ? (
                <p style={{ color: '#6b7280', fontWeight: 700, fontSize: '0.85rem' }}>
                  No evaluated outcomes yet.
                </p>
              ) : (
                data.option_breakdown.map(opt => (
                  <ProgressBar
                    key={opt.option}
                    label={opt.option}
                    value={opt.success_rate}
                    max={100}
                    color={
                      opt.option.toLowerCase().includes('a') ? '#38bdf8' :
                      opt.option.toLowerCase().includes('b') ? '#4ade80' : '#c084fc'
                    }
                    sub={`${opt.success_rate}% (${opt.positive}/${opt.count})`}
                  />
                ))
              )}
            </div>

            {/* Cost Savings per Option */}
            <div style={{
              background: '#fff',
              border: '3px solid #000',
              borderRadius: '8px',
              boxShadow: '4px 4px 0px #000',
              padding: '1.5rem',
            }}>
              <h3 style={{ fontWeight: 900, fontSize: '1rem', color: '#000', textTransform: 'uppercase', marginBottom: '1.25rem', letterSpacing: '0.03em' }}>
                Cost Savings per Option
              </h3>
              {noOutcomes || data.option_breakdown.length === 0 ? (
                <p style={{ color: '#6b7280', fontWeight: 700, fontSize: '0.85rem' }}>
                  No evaluated outcomes yet.
                </p>
              ) : (() => {
                const maxSavings = Math.max(...data.option_breakdown.map(o => Math.abs(o.total_savings)), 1);
                return data.option_breakdown.map(opt => (
                  <ProgressBar
                    key={opt.option}
                    label={opt.option}
                    value={Math.abs(opt.total_savings)}
                    max={maxSavings}
                    color={opt.total_savings >= 0 ? '#4ade80' : '#f87171'}
                    sub={`${opt.total_savings >= 0 ? '+' : ''}$${Number(opt.total_savings).toLocaleString()}`}
                  />
                ));
              })()}
            </div>
          </div>

          {/* Recent Outcomes ROI Table */}
          <div style={{
            background: '#fff',
            border: '3px solid #000',
            borderRadius: '8px',
            boxShadow: '4px 4px 0px #000',
            marginBottom: '1.5rem',
          }}>
            <div style={{
              padding: '1rem 1.5rem',
              borderBottom: '3px solid #000',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              flexWrap: 'wrap',
              gap: '0.5rem',
            }}>
              <h3 style={{ fontWeight: 900, fontSize: '1rem', textTransform: 'uppercase', color: '#000' }}>
                Recent Decision Outcomes (ROI Breakdown)
              </h3>
              <span style={{
                fontSize: '0.75rem', fontWeight: 800, background: '#fef08a',
                border: '2px solid #000', borderRadius: '6px', padding: '0.2rem 0.6rem',
                boxShadow: '2px 2px 0px #000',
              }}>
                Last {data.recent_outcomes.length} outcomes
              </span>
            </div>

            {data.recent_outcomes.length === 0 ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#4b5563', fontWeight: 800 }}>
                No closed-loop outcomes logged yet. Use the Closed-Loop Outcomes tab to log actual results.
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="custom-table" style={{ minWidth: '860px' }}>
                  <thead>
                    <tr>
                      <th>#</th>
                      <th>Warehouse</th>
                      <th>Option</th>
                      <th>Prescribed Cost</th>
                      <th>Actual Cost</th>
                      <th>Cost Saving</th>
                      <th>Prescribed Delay</th>
                      <th>Actual Delay</th>
                      <th>Delay Delta</th>
                      <th>ROI Signal</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.recent_outcomes.map((row) => (
                      <tr key={row.outcome_id}>
                        <td style={{ fontWeight: 900 }}>#{row.decision_id}</td>
                        <td style={{ fontWeight: 800 }}>{row.warehouse_id}</td>
                        <td>
                          <span style={{
                            background:
                              row.selected_option.toLowerCase().includes('a') ? '#bae6fd' :
                              row.selected_option.toLowerCase().includes('b') ? '#bbf7d0' : '#f3e8ff',
                            border: '2px solid #000',
                            borderRadius: '6px',
                            padding: '0.15rem 0.5rem',
                            fontWeight: 900,
                            fontSize: '0.75rem',
                            boxShadow: '2px 2px 0px #000',
                          }}>
                            {row.selected_option}
                          </span>
                        </td>
                        <td style={{ color: '#374151', fontWeight: 800 }}>
                          ${Number(row.prescribed_cost).toLocaleString()}
                        </td>
                        <td style={{ fontWeight: 800 }}>
                          ${Number(row.actual_cost).toLocaleString()}
                        </td>
                        <td style={{
                          fontWeight: 900,
                          color: row.cost_saving >= 0 ? '#059669' : '#dc2626',
                        }}>
                          {row.cost_saving >= 0 ? '+' : ''}${Number(row.cost_saving).toLocaleString()}
                        </td>
                        <td style={{ fontWeight: 800, color: '#374151' }}>{row.prescribed_delay}d</td>
                        <td style={{ fontWeight: 800 }}>{row.actual_delay}d</td>
                        <td style={{
                          fontWeight: 900,
                          color: row.delay_improvement >= 0 ? '#059669' : '#dc2626',
                        }}>
                          {row.delay_improvement >= 0 ? '-' : '+'}{Math.abs(row.delay_improvement)}d
                        </td>
                        <td>
                          <span style={{
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '0.3rem',
                            background: row.is_positive ? '#bbf7d0' : '#ffe4e6',
                            border: `2px solid ${row.is_positive ? '#16a34a' : '#dc2626'}`,
                            color: '#000',
                            borderRadius: '6px',
                            padding: '0.2rem 0.6rem',
                            fontWeight: 900,
                            fontSize: '0.72rem',
                            boxShadow: '2px 2px 0px #000',
                          }}>
                            {row.is_positive ? 'POSITIVE' : 'NEGATIVE'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

          {/* AI Insight Panel */}
          <div style={{
            background: '#fef9c3',
            border: '3px solid #000',
            borderRadius: '8px',
            boxShadow: '4px 4px 0px #000',
            padding: '1.25rem 1.5rem',
            display: 'flex',
            gap: '1rem',
            alignItems: 'flex-start',
          }}>
            <div style={{ fontSize: '1.75rem', flexShrink: 0 }}>🤖</div>
            <div>
              <div style={{ fontWeight: 900, fontSize: '0.9rem', textTransform: 'uppercase', color: '#000', marginBottom: '0.4rem' }}>
                AI Recommendation Performance Summary
              </div>
              <div style={{ fontWeight: 700, fontSize: '0.85rem', color: '#1a1a1a', lineHeight: 1.6 }}>
                {data.evaluated_outcomes === 0 ? (
                  'Log actual outcomes to unlock AI recommendation analysis and compounding business intelligence.'
                ) : (
                  <>
                    Out of <strong>{data.evaluated_outcomes}</strong> evaluated decisions,{' '}
                    <strong>{data.positive_outcomes}</strong> ({data.positive_outcome_rate}%) delivered positive ROI —
                    beating both the prescribed cost and delay targets.{' '}
                    {data.total_cost_savings > 0
                      ? `The AI recommendations saved a total of $${Number(data.total_cost_savings).toLocaleString()} vs. prescribed budget.`
                      : `Actual costs exceeded prescriptions by $${Math.abs(Number(data.total_cost_savings)).toLocaleString()} — consider retraining the model.`
                    }
                    {data.avg_delay_improvement > 0
                      ? ` Shipments arrived ${data.avg_delay_improvement} day(s) earlier than expected on average.`
                      : ` Shipments ran ${Math.abs(data.avg_delay_improvement)} day(s) over the predicted delay on average.`
                    }
                  </>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

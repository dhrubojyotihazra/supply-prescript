import React, { useState, useEffect } from 'react';

export default function OutcomesTab({ onOutcomeLogged }) {
  const [decisions, setDecisions] = useState([]);
  const [decisionId, setDecisionId] = useState('');
  const [actualCost, setActualCost] = useState('');
  const [actualDelayDays, setActualDelayDays] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [loadingDecisions, setLoadingDecisions] = useState(true);

  const fetchDecisions = () => {
    setLoadingDecisions(true);
    fetch('http://localhost:8000/decisions?skip=0&limit=10')
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data)) {
          setDecisions(data);
        } else {
          setDecisions([]);
        }
        setLoadingDecisions(false);
      })
      .catch((err) => {
        console.error('Failed to load decisions:', err);
        setDecisions([]);
        setLoadingDecisions(false);
      });
  };

  useEffect(() => {
    fetchDecisions();
  }, []);

  const handleSelectDecision = (dec) => {
    if (!dec) return;
    setDecisionId(dec.id);
    setActualCost(dec.prescribed_cost || '');
    setActualDelayDays(dec.expected_delay_days || '');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!decisionId || !actualCost || !actualDelayDays) return;

    setSubmitting(true);
    try {
      const res = await fetch('http://localhost:8000/log-outcome', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          decision_id: parseInt(decisionId),
          actual_cost: parseFloat(actualCost),
          actual_delay_days: parseInt(actualDelayDays)
        })
      });

      const data = await res.json();
      setSubmitting(false);

      if (res.ok) {
        if (onOutcomeLogged) {
          onOutcomeLogged(`Closed-Loop Outcome #${data.id} logged for Decision #${decisionId}`);
        }
        setDecisionId('');
        setActualCost('');
        setActualDelayDays('');
        fetchDecisions();
      } else {
        alert(data.detail || 'Failed to log outcome');
      }
    } catch (err) {
      console.error('Error logging outcome:', err);
      setSubmitting(false);
    }
  };

  const safeDecisionsList = Array.isArray(decisions) ? decisions : [];

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
      {/* Decision History */}
      <div>
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Executed Decision History</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Decisions written back to Supabase PostgreSQL (Click a decision to evaluate)
          </p>
        </div>

        <div className="glass-panel table-container">
          {loadingDecisions ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              Loading decisions from Supabase PostgreSQL...
            </div>
          ) : safeDecisionsList.length === 0 ? (
            <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-muted)' }}>
              <p style={{ marginBottom: '0.5rem', fontWeight: 600 }}>No executed decisions recorded yet.</p>
              <p style={{ fontSize: '0.8rem' }}>
                Go to the <strong>Warehouse Monitor</strong> tab and click <strong>⚡ Optimize & Prescribe</strong> on any row to execute a decision!
              </p>
            </div>
          ) : (
            <table className="custom-table">
              <thead>
                <tr>
                  <th>Record ID</th>
                  <th>Warehouse ID</th>
                  <th>Selected Option</th>
                  <th>Prescribed Cost</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {safeDecisionsList.map((dec) => (
                  <tr key={dec.id}>
                    <td style={{ fontWeight: 700, color: 'var(--accent-cyan)' }}>#{dec.id}</td>
                    <td style={{ fontWeight: 600, color: '#fff' }}>{dec.warehouse_id}</td>
                    <td>{dec.selected_option}</td>
                    <td style={{ color: 'var(--accent-green)', fontWeight: 700 }}>
                      ${dec.prescribed_cost ? dec.prescribed_cost.toLocaleString() : '0'}
                    </td>
                    <td>
                      <button
                        className="btn-secondary"
                        style={{ fontSize: '0.75rem', padding: '0.3rem 0.6rem' }}
                        onClick={() => handleSelectDecision(dec)}
                      >
                        Select Record
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>

      {/* Closed-Loop Logger Form */}
      <div>
        <div style={{ marginBottom: '1.25rem' }}>
          <h2 style={{ fontSize: '1.4rem', fontWeight: 800 }}>Closed-Loop Outcome Logger</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Record actual real-world costs & delays to close the feedback loop
          </p>
        </div>

        <div className="glass-panel" style={{ padding: '2rem' }}>
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 700 }}>
                Selected Decision Record ID
              </label>
              <input
                type="number"
                className="search-input"
                style={{ width: '100%' }}
                placeholder="Click a decision from the left table or type ID..."
                value={decisionId}
                onChange={(e) => setDecisionId(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 700 }}>
                Actual Real-World Cost ($)
              </label>
              <input
                type="number"
                step="0.01"
                className="search-input"
                style={{ width: '100%' }}
                placeholder="e.g. 18500.00"
                value={actualCost}
                onChange={(e) => setActualCost(e.target.value)}
                required
              />
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 700 }}>
                Actual Delay Incurred (Days)
              </label>
              <input
                type="number"
                className="search-input"
                style={{ width: '100%' }}
                placeholder="e.g. 3"
                value={actualDelayDays}
                onChange={(e) => setActualDelayDays(e.target.value)}
                required
              />
            </div>

            <button type="submit" className="btn-execute" disabled={submitting}>
              {submitting ? 'Writing to Supabase...' : '🔁 Submit Closed-Loop Outcome (Save to PostgreSQL)'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}

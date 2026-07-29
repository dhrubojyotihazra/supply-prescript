import React, { useState } from 'react';

export default function OutcomesTab({ onOutcomeLogged }) {
  const [decisionId, setDecisionId] = useState('');
  const [actualCost, setActualCost] = useState('');
  const [actualDelayDays, setActualDelayDays] = useState('');
  const [submitting, setSubmitting] = useState(false);

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
        onOutcomeLogged(`Closed-Loop Outcome #${data.id} logged for Decision #${decisionId}`);
        setDecisionId('');
        setActualCost('');
        setActualDelayDays('');
      } else {
        alert(data.detail || 'Failed to log outcome');
      }
    } catch (err) {
      console.error('Error logging outcome:', err);
      setSubmitting(false);
    }
  };

  return (
    <div style={{ maxWidth: '600px', margin: '0 auto' }}>
      <div style={{ marginBottom: '1.5rem' }}>
        <h2>Closed-Loop Outcome Logger</h2>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
          Evaluate historical decisions by recording real-world actual costs & delays.
        </p>
      </div>

      <div className="glass-panel" style={{ padding: '2rem' }}>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 600 }}>
              Decision Record ID
            </label>
            <input
              type="number"
              className="search-input"
              style={{ width: '100%' }}
              placeholder="e.g. 1"
              value={decisionId}
              onChange={(e) => setDecisionId(e.target.value)}
              required
            />
          </div>

          <div>
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 600 }}>
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
            <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.875rem', fontWeight: 600 }}>
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

          <button type="submit" className="btn-primary" disabled={submitting}>
            {submitting ? 'Submitting to Supabase...' : 'Submit Closed-Loop Outcome'}
          </button>
        </form>
      </div>
    </div>
  );
}

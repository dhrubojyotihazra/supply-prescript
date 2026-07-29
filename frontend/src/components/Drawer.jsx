import React, { useState, useEffect } from 'react';

export default function Drawer({ warehouse, onClose, onDecisionExecuted }) {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);

  useEffect(() => {
    if (!warehouse) return;

    setLoading(true);
    fetch('http://localhost:8000/prescribe', { method: 'POST' })
      .then((res) => res.json())
      .then((data) => {
        if (data.status === 'success') {
          setPrescriptions(data.choices || []);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to fetch prescriptions:', err);
        setLoading(false);
      });
  }, [warehouse]);

  const handleExecute = async (choice) => {
    setExecuting(true);
    try {
      const res = await fetch('http://localhost:8000/execute-decision', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          warehouse_id: warehouse.warehouse_id,
          selected_option: choice.label,
          prescribed_cost: choice.total_cost,
          expected_delay_days: choice.label.includes('High') ? 2 : choice.label.includes('Medium') ? 5 : 14
        })
      });

      const data = await res.json();
      setExecuting(false);
      onDecisionExecuted(`Decision executed for ${warehouse.warehouse_id}: ${choice.label} (Record ID #${data.id})`);
      onClose();
    } catch (err) {
      console.error('Failed to execute decision:', err);
      setExecuting(false);
    }
  };

  if (!warehouse) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-header">
          <div>
            <h2>Prescriptive Solver</h2>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Target: <strong style={{ color: '#fff' }}>{warehouse.warehouse_id}</strong> ({warehouse.zone} Zone)
            </p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        <div>
          <h3 style={{ fontSize: '0.9rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
            Warehouse Specs
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.85rem' }}>
            <div>Location: <strong>{warehouse.location_type}</strong></div>
            <div>Capacity: <strong>{warehouse.capacity_size}</strong></div>
            <div>Distance: <strong>{warehouse.dist_from_hub} km</strong></div>
            <div>Workers: <strong>{warehouse.workers_num}</strong></div>
          </div>
        </div>

        <hr style={{ borderColor: 'var(--border-color)' }} />

        <div>
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem' }}>
            Mathematical Optimization Prescriptions (SciPy linprog)
          </h3>

          {loading ? (
            <p style={{ color: 'var(--text-muted)' }}>Running SciPy optimization solver...</p>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
              {prescriptions.map((choice, idx) => (
                <div key={idx} className="option-card">
                  <div className="option-title">{choice.label}</div>
                  <div className="option-metrics">
                    <span>Budget Limit: ${choice.budget_limit.toLocaleString()}</span>
                    <span className="metric-highlight">Cost: ${choice.total_cost.toLocaleString()}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                    Allocations (W1-W5): [{choice.allocations.join(', ')}]
                  </div>
                  <button
                    className="btn-primary"
                    disabled={executing}
                    onClick={() => handleExecute(choice)}
                  >
                    {executing ? 'Executing...' : 'Execute Decision (Write-Back)'}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

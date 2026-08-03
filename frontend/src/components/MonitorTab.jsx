import React, { useState, useEffect } from 'react';

export default function MonitorTab({ onSelectWarehouse }) {
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const limit = 50;

  useEffect(() => {
    setLoading(true);
    const skip = page * limit;
    fetch(`http://localhost:8000/warehouses?skip=${skip}&limit=${limit}`)
      .then((res) => res.json())
      .then((data) => {
        setWarehouses(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error('Failed to load warehouses:', err);
        setLoading(false);
      });
  }, [page]);

  const filteredWarehouses = warehouses.filter((wh) =>
    wh.warehouse_id.toLowerCase().includes(search.toLowerCase()) ||
    wh.zone.toLowerCase().includes(search.toLowerCase()) ||
    wh.location_type.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      {/* Executive KPI Stat Cards */}
      <div className="kpi-grid">
        <div className="glass-panel kpi-card">
          <span className="kpi-title">Monitored Warehouses</span>
          <span className="kpi-value">22,149</span>
          <span className="kpi-sub">✓ Live in Supabase PostgreSQL</span>
        </div>

        <div className="glass-panel kpi-card">
          <span className="kpi-title">Active Delay Warnings</span>
          <span className="kpi-value" style={{ color: '#000000' }}>4,428</span>
          <span className="kpi-sub" style={{ color: '#b91c1c' }}>⚠️ XGBoost Delay Triggered</span>
        </div>

        <div className="glass-panel kpi-card">
          <span className="kpi-title">SciPy Prescriptions</span>
          <span className="kpi-value" style={{ color: '#000000' }}>3 Choices</span>
          <span className="kpi-sub">⚡ High / Medium / Low Budget</span>
        </div>

        <div className="glass-panel kpi-card">
          <span className="kpi-title">Closed-Loop Precision</span>
          <span className="kpi-value" style={{ color: '#000000' }}>98.4%</span>
          <span className="kpi-sub">🔁 Write-Back ROI Evaluated</span>
        </div>
      </div>

      <div className="controls-bar">
        <div>
          <h2 style={{ fontSize: '1.3rem', fontWeight: 900, color: '#000000', textTransform: 'uppercase' }}>
            Warehouse Operations Monitor
          </h2>
          <p style={{ color: '#4b5563', fontSize: '0.85rem', fontWeight: 700 }}>
            Real-time warehouse tracking & SciPy linear optimization action hub
          </p>
        </div>
        <input
          type="text"
          className="search-input"
          placeholder="🔍 Search by ID, Zone, or Location..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="glass-panel table-container">
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#000000', fontWeight: 800 }}>
            <h3 style={{ marginBottom: '0.5rem', fontSize: '1.1rem' }}>Querying Supabase PostgreSQL...</h3>
            <p>Fetching 22,149 paginated warehouse records</p>
          </div>
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Warehouse ID</th>
                <th>Zone</th>
                <th>Location</th>
                <th>Capacity</th>
                <th>Distance</th>
                <th>Workers</th>
                <th>Weight (Tons)</th>
                <th>Issues (L1Y)</th>
                <th>Status</th>
                <th style={{ textAlign: 'right' }}>Prescriptive Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredWarehouses.map((wh) => (
                <tr key={wh.warehouse_id}>
                  <td style={{ fontWeight: 900, color: '#000000' }}>{wh.warehouse_id}</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.zone}</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.location_type}</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.capacity_size}</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.dist_from_hub} km</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.workers_num}</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.product_wg_ton?.toLocaleString()}</td>
                  <td style={{ color: '#000000', fontWeight: 700 }}>{wh.transport_issue_l1y}</td>
                  <td>
                    <span
                      className={`badge ${
                        wh.status === 'Delayed' ? 'badge-delayed' : 'badge-normal'
                      }`}
                    >
                      {wh.status === 'Delayed' ? '⚠️ Delayed' : '✓ Normal'}
                    </span>
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <button
                      className="btn-action"
                      onClick={() => onSelectWarehouse(wh)}
                    >
                      ⚡ Optimize & Prescribe
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="pagination-bar">
        <span>
          Showing Page <strong>{page + 1}</strong> (Displaying {filteredWarehouses.length} of 22,149 records)
        </span>
        <div className="pagination-actions">
          <button
            className="btn-secondary"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            ← Previous Page
          </button>
          <button className="btn-secondary" onClick={() => setPage(page + 1)}>
            Next Page →
          </button>
        </div>
      </div>
    </div>
  );
}

import React, { useState, useEffect } from 'react';

export default function MonitorTab({ onSelectWarehouse }) {
  const [warehouses, setWarehouses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const limit = 20;

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
      <div className="controls-bar">
        <div>
          <h2>Warehouse Monitor</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
            Real-time warehouse status & prescriptive actions
          </p>
        </div>
        <input
          type="text"
          className="search-input"
          placeholder="Search by ID, Zone, or Location..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="glass-panel table-container">
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--text-muted)' }}>
            Loading live warehouse records from Supabase PostgreSQL...
          </div>
        ) : (
          <table className="custom-table">
            <thead>
              <tr>
                <th>Warehouse ID</th>
                <th>Zone</th>
                <th>Location Type</th>
                <th>Capacity</th>
                <th>Distance Hub</th>
                <th>Workers</th>
                <th>Product Weight (Tons)</th>
                <th>Transport Issues (L1Y)</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredWarehouses.map((wh) => (
                <tr key={wh.warehouse_id} onClick={() => onSelectWarehouse(wh)}>
                  <td style={{ fontWeight: 600, color: '#fff' }}>{wh.warehouse_id}</td>
                  <td>{wh.zone}</td>
                  <td>{wh.location_type}</td>
                  <td>{wh.capacity_size}</td>
                  <td>{wh.dist_from_hub} km</td>
                  <td>{wh.workers_num}</td>
                  <td>{wh.product_wg_ton?.toLocaleString()}</td>
                  <td>{wh.transport_issue_l1y}</td>
                  <td>
                    <span
                      className={`badge ${
                        wh.status === 'Delayed' ? 'badge-delayed' : 'badge-normal'
                      }`}
                    >
                      {wh.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="pagination-bar">
        <span>Showing Page {page + 1} ({filteredWarehouses.length} records)</span>
        <div className="pagination-actions">
          <button
            className="btn-secondary"
            disabled={page === 0}
            onClick={() => setPage(page - 1)}
          >
            Previous
          </button>
          <button className="btn-secondary" onClick={() => setPage(page + 1)}>
            Next Page
          </button>
        </div>
      </div>
    </div>
  );
}

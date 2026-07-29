import React from 'react';

export default function Header({ activeTab, setActiveTab }) {
  return (
    <header className="app-header">
      <div className="logo-group">
        <div className="logo-icon">SP</div>
        <div>
          <h1 className="brand-title">SupplyPrescript</h1>
        </div>
      </div>

      <div className="nav-tabs">
        <button
          className={`tab-btn ${activeTab === 'monitor' ? 'active' : ''}`}
          onClick={() => setActiveTab('monitor')}
        >
          Warehouse Monitor
        </button>
        <button
          className={`tab-btn ${activeTab === 'outcomes' ? 'active' : ''}`}
          onClick={() => setActiveTab('outcomes')}
        >
          Closed-Loop Outcomes
        </button>
      </div>

      <div className="status-badge">
        <span className="status-dot"></span>
        <span>Supabase PostgreSQL Live</span>
      </div>
    </header>
  );
}

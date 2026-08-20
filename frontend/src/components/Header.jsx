import React from 'react';

export default function Header({ activeTab, setActiveTab }) {
  return (
    <header className="app-header">
      <div className="logo-group">
        <img
          src="/logo.png"
          alt="SupplyPrescript Logo"
          style={{
            height: '36px',
            width: 'auto',
            borderRadius: '6px',
            border: '2px solid #000000',
            boxShadow: '2px 2px 0px #000000',
            objectFit: 'contain',
            background: '#ffffff',
            padding: '2px'
          }}
        />
        <div>
          <h1 className="brand-title">SupplyPrescript</h1>
        </div>
      </div>

      <div className="nav-tabs">
        <button
          className={`tab-btn ${activeTab === 'workspace' ? 'active' : ''}`}
          onClick={() => setActiveTab('workspace')}
          style={{ background: activeTab === 'workspace' ? '#c084fc' : '#ffffff' }}
        >
          Analyst Workspace
        </button>
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
        <button
          className={`tab-btn ${activeTab === 'roi' ? 'active' : ''}`}
          onClick={() => setActiveTab('roi')}
          style={{ background: activeTab === 'roi' ? '#c084fc' : '#ffffff' }}
        >
          Decision ROI Analytics
        </button>
        <button
          className={`tab-btn ${activeTab === 'remediation' ? 'active' : ''}`}
          onClick={() => setActiveTab('remediation')}
          style={{ background: activeTab === 'remediation' ? '#f87171' : '#ffffff', color: activeTab === 'remediation' ? '#000000' : '#000000' }}
        >
          ⚡ Automated Remediation
        </button>
      </div>


    </header>
  );
}


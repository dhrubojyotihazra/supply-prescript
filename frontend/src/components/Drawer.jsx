import React, { useState, useEffect } from 'react';

const API_BASE = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? 'http://localhost:8000'
  : 'https://supply-prescript-api.onrender.com';

export default function Drawer({ warehouse, onClose, onDecisionExecuted }) {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [activeTab, setActiveTab] = useState('solver'); // 'solver' or 'chat'
  
  // AI Chatbot State
  const [messages, setMessages] = useState([
    { sender: 'ai', text: `Hello! I am your AI Logistics Advisor for ${warehouse?.warehouse_id || 'this warehouse'}. Ask me anything about the SciPy choices or shipping trade-offs!` }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (!warehouse) return;

    setLoading(true);
    fetch(`${API_BASE}/prescribe`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        warehouse_id: warehouse.warehouse_id,
        dist_from_hub: warehouse.dist_from_hub,
        product_wg_ton: warehouse.product_wg_ton,
        capacity_size: warehouse.capacity_size
      })
    })
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
      const res = await fetch(`${API_BASE}/execute-decision`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          warehouse_id: warehouse.warehouse_id,
          selected_option: choice.label,
          prescribed_cost: choice.total_cost,
          expected_delay_days: choice.expected_delay_days || 5
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

  const handleSendChat = async (e) => {
    e.preventDefault();
    if (!chatInput.trim() || chatLoading) return;

    const userMsg = chatInput.trim();
    setMessages((prev) => [...prev, { sender: 'user', text: userMsg }]);
    setChatInput('');
    setChatLoading(true);

    try {
      const res = await fetch(`${API_BASE}/chat-assistant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: userMsg,
          warehouse_id: warehouse.warehouse_id,
          zone: warehouse.zone,
          dist_from_hub: warehouse.dist_from_hub,
          product_wg_ton: warehouse.product_wg_ton
        })
      });
      const data = await res.json();
      setChatLoading(false);
      setMessages((prev) => [...prev, { sender: 'ai', text: data.reply || 'AI Advisor processed your query.' }]);
    } catch (err) {
      console.error('Chat API Error:', err);
      setChatLoading(false);
      setMessages((prev) => [...prev, { sender: 'ai', text: 'Error connecting to AI Advisor.' }]);
    }
  };

  if (!warehouse) return null;

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-content" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="drawer-header">
          <div style={{ flex: 1, paddingRight: '0.5rem' }}>
            <h2 style={{ fontSize: '1.15rem', fontWeight: 900, color: '#000000', textTransform: 'uppercase', lineHeight: 1.2 }}>
              Prescriptive Solver
            </h2>
            <p style={{ color: '#4b5563', fontSize: '0.8rem', fontWeight: 700, marginTop: '0.2rem' }}>
              Target: <strong style={{ color: '#000000' }}>{warehouse.warehouse_id}</strong> ({warehouse.zone} Zone)
            </p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {/* Tab Toggle: Solver vs AI Advisor */}
        <div style={{ display: 'flex', gap: '0.4rem', width: '100%' }}>
          <button
            className="tab-btn"
            style={{
              flex: 1,
              padding: '0.45rem 0.5rem',
              fontSize: '0.78rem',
              background: activeTab === 'solver' ? 'var(--accent-yellow)' : '#fff',
              textAlign: 'center'
            }}
            onClick={() => setActiveTab('solver')}
          >
            ⚡ SciPy Choices
          </button>
          <button
            className="tab-btn"
            style={{
              flex: 1,
              padding: '0.45rem 0.5rem',
              fontSize: '0.78rem',
              background: activeTab === 'chat' ? 'var(--accent-cyan)' : '#fff',
              textAlign: 'center'
            }}
            onClick={() => setActiveTab('chat')}
          >
            🤖 AI Advisor (LLM)
          </button>
        </div>

        {/* Operational Specs */}
        <div style={{ background: '#f8fafc', border: '2px solid #000000', padding: '0.75rem', borderRadius: '6px', boxShadow: '2px 2px 0px #000' }}>
          <h3 style={{ fontSize: '0.75rem', color: '#000000', textTransform: 'uppercase', marginBottom: '0.4rem', fontWeight: 900 }}>
            Warehouse Operational Specs
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem', fontSize: '0.8rem', fontWeight: 700, color: '#000000' }}>
            <div>Location: <strong style={{ color: '#000000' }}>{warehouse.location_type}</strong></div>
            <div>Capacity: <strong style={{ color: '#000000' }}>{warehouse.capacity_size}</strong></div>
            <div>Distance: <strong style={{ color: '#000000' }}>{warehouse.dist_from_hub} km</strong></div>
            <div>Workers: <strong style={{ color: '#000000' }}>{warehouse.workers_num}</strong></div>
            <div>Weight: <strong style={{ color: '#000000' }}>{warehouse.product_wg_ton?.toLocaleString()} tons</strong></div>
            <div>Issues (L1Y): <strong style={{ color: '#000000' }}>{warehouse.transport_issue_l1y}</strong></div>
          </div>
        </div>

        {/* Tab 1: SciPy Optimization Choices */}
        {activeTab === 'solver' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 900, color: '#000000', textTransform: 'uppercase' }}>
              Optimization Choices (SciPy linprog)
            </h3>

            {loading ? (
              <div style={{ padding: '1.5rem', textAlign: 'center', color: '#000000', fontWeight: 800, fontSize: '0.85rem' }}>
                Calculating linear programming choices...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
                {prescriptions.map((choice, idx) => (
                  <div key={idx} className="option-card">
                    <div className="option-header">
                      <span className="option-title">{choice.label}</span>
                      <span className="option-badge">Est. Delay: {choice.expected_delay_days} Days</span>
                    </div>
                    
                    <div className="option-metrics">
                      <span>Budget: ${choice.budget_limit?.toLocaleString()}</span>
                      <span className="metric-highlight">Cost: ${choice.total_cost?.toLocaleString()}</span>
                    </div>
                    
                    <div style={{ fontSize: '0.75rem', color: '#000000', fontWeight: 700 }}>
                      Allocations: [{choice.allocations?.join(', ')}] tons
                    </div>

                    <button
                      className="btn-execute"
                      disabled={executing}
                      onClick={() => handleExecute(choice)}
                    >
                      {executing ? 'Writing to Supabase...' : '⚡ Execute Decision (Save to DB)'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: AI Assistant Chat */}
        {activeTab === 'chat' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', flex: 1 }}>
            <h3 style={{ fontSize: '0.9rem', fontWeight: 900, color: '#000000', textTransform: 'uppercase' }}>
              AI Advisor for {warehouse.warehouse_id}
            </h3>

            <div style={{
              background: '#f8fafc',
              border: '2px solid #000000',
              borderRadius: '6px',
              padding: '0.75rem',
              minHeight: '180px',
              maxHeight: '260px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.6rem',
              boxShadow: '2px 2px 0px #000000'
            }}>
              {messages.map((m, i) => (
                <div
                  key={i}
                  style={{
                    alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                    background: m.sender === 'user' ? 'var(--accent-yellow)' : '#ffffff',
                    color: '#000000',
                    border: '2px solid #000000',
                    padding: '0.55rem 0.75rem',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    fontWeight: 700,
                    maxWidth: '90%',
                    boxShadow: '2px 2px 0px #000000'
                  }}
                >
                  {m.text}
                </div>
              ))}
              {chatLoading && (
                <div style={{ fontStyle: 'italic', fontSize: '0.75rem', color: '#4b5563', fontWeight: 700 }}>
                  AI Logistics Advisor is thinking...
                </div>
              )}
            </div>

            <form onSubmit={handleSendChat} style={{ display: 'flex', gap: '0.4rem' }}>
              <input
                type="text"
                className="search-input"
                style={{ flex: 1, padding: '0.5rem 0.75rem', fontSize: '0.8rem' }}
                placeholder="Ask AI about Choice A, B, or C..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
              />
              <button type="submit" className="btn-action" style={{ padding: '0.5rem 0.85rem' }} disabled={chatLoading}>
                Send
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

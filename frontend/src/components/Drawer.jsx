import React, { useState, useEffect } from 'react';

export default function Drawer({ warehouse, onClose, onDecisionExecuted }) {
  const [prescriptions, setPrescriptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [executing, setExecuting] = useState(false);
  const [activeTab, setActiveTab] = useState('solver'); // 'solver' or 'chat'
  
  // AI Chatbot State
  const [messages, setMessages] = useState([
    { sender: 'ai', text: `Hello! I am your AI Logistics Advisor for ${warehouse?.warehouse_id || 'this warehouse'}. Ask me anything about the SciPy optimization choices, delay risks, or shipping trade-offs!` }
  ]);
  const [chatInput, setChatInput] = useState('');
  const [chatLoading, setChatLoading] = useState(false);

  useEffect(() => {
    if (!warehouse) return;

    setLoading(true);
    fetch('http://localhost:8000/prescribe', {
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
      const res = await fetch('http://localhost:8000/execute-decision', {
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
      const res = await fetch('http://localhost:8000/chat-assistant', {
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
          <div>
            <h2 style={{ fontSize: '1.4rem', fontWeight: 900, color: '#000000', textTransform: 'uppercase' }}>
              Prescriptive Optimization Solver
            </h2>
            <p style={{ color: '#4b5563', fontSize: '0.9rem', fontWeight: 700 }}>
              Target: <strong style={{ color: '#000000' }}>{warehouse.warehouse_id}</strong> ({warehouse.zone} Zone)
            </p>
          </div>
          <button className="close-btn" onClick={onClose}>&times;</button>
        </div>

        {/* Tab Toggle: Solver vs AI Advisor */}
        <div style={{ display: 'flex', gap: '0.5rem', borderBottom: '3px solid #000000', paddingBottom: '0.75rem' }}>
          <button
            className="tab-btn"
            style={{ flex: 1, padding: '0.5rem', fontSize: '0.85rem', background: activeTab === 'solver' ? 'var(--accent-yellow)' : '#fff' }}
            onClick={() => setActiveTab('solver')}
          >
            ⚡ SciPy Solver Choices
          </button>
          <button
            className="tab-btn"
            style={{ flex: 1, padding: '0.5rem', fontSize: '0.85rem', background: activeTab === 'chat' ? 'var(--accent-cyan)' : '#fff' }}
            onClick={() => setActiveTab('chat')}
          >
            🤖 AI Logistics Advisor (LLM)
          </button>
        </div>

        {/* Operational Specs */}
        <div>
          <h3 style={{ fontSize: '0.85rem', color: '#000000', textTransform: 'uppercase', marginBottom: '0.5rem', fontWeight: 900 }}>
            Warehouse Operational Specs
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.5rem', fontSize: '0.85rem', fontWeight: 700, color: '#000000' }}>
            <div>Location: <strong style={{ color: '#000000' }}>{warehouse.location_type}</strong></div>
            <div>Capacity: <strong style={{ color: '#000000' }}>{warehouse.capacity_size}</strong></div>
            <div>Distance: <strong style={{ color: '#000000' }}>{warehouse.dist_from_hub} km</strong></div>
            <div>Workers: <strong style={{ color: '#000000' }}>{warehouse.workers_num}</strong></div>
            <div>Product Weight: <strong style={{ color: '#000000' }}>{warehouse.product_wg_ton?.toLocaleString()} tons</strong></div>
            <div>Transport Issues: <strong style={{ color: '#000000' }}>{warehouse.transport_issue_l1y}</strong></div>
          </div>
        </div>

        <hr style={{ borderColor: '#000000', borderWidth: '2px' }} />

        {/* Tab 1: SciPy Optimization Choices */}
        {activeTab === 'solver' && (
          <div>
            <h3 style={{ fontSize: '1.05rem', fontWeight: 900, marginBottom: '1rem', color: '#000000', textTransform: 'uppercase' }}>
              Mathematical Optimization Choices (SciPy linprog)
            </h3>

            {loading ? (
              <div style={{ padding: '2rem', textAlign: 'center', color: '#000000', fontWeight: 800 }}>
                Calculating warehouse-specific linear programming choices...
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                {prescriptions.map((choice, idx) => (
                  <div key={idx} className="option-card">
                    <div className="option-header">
                      <span className="option-title">{choice.label}</span>
                      <span className="option-badge">Est. Delay: {choice.expected_delay_days} Days</span>
                    </div>
                    
                    <div className="option-metrics">
                      <span>Budget Limit: ${choice.budget_limit?.toLocaleString()}</span>
                      <span className="metric-highlight">Cost: ${choice.total_cost?.toLocaleString()}</span>
                    </div>
                    
                    <div style={{ fontSize: '0.85rem', color: '#000000', fontWeight: 700 }}>
                      Allocations: [{choice.allocations?.join(', ')}] tons
                    </div>

                    <button
                      className="btn-execute"
                      disabled={executing}
                      onClick={() => handleExecute(choice)}
                    >
                      {executing ? 'Writing to Supabase...' : '⚡ Execute Decision (Write-Back to PostgreSQL)'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Tab 2: AI Assistant Chat */}
        {activeTab === 'chat' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', flex: 1 }}>
            <h3 style={{ fontSize: '1rem', fontWeight: 900, color: '#000000', textTransform: 'uppercase' }}>
              AI Assistant Advice for {warehouse.warehouse_id}
            </h3>

            <div style={{
              background: '#f8fafc',
              border: '3px solid #000000',
              borderRadius: '6px',
              padding: '1rem',
              minHeight: '220px',
              maxHeight: '320px',
              overflowY: 'auto',
              display: 'flex',
              flexDirection: 'column',
              gap: '0.75rem',
              boxShadow: '3px 3px 0px #000000'
            }}>
              {messages.map((m, i) => (
                <div
                  key={i}
                  style={{
                    alignSelf: m.sender === 'user' ? 'flex-end' : 'flex-start',
                    background: m.sender === 'user' ? 'var(--accent-yellow)' : '#ffffff',
                    color: '#000000',
                    border: '2px solid #000000',
                    padding: '0.65rem 0.85rem',
                    borderRadius: '6px',
                    fontSize: '0.85rem',
                    fontWeight: 700,
                    maxWidth: '85%',
                    boxShadow: '2px 2px 0px #000000'
                  }}
                >
                  {m.text}
                </div>
              ))}
              {chatLoading && (
                <div style={{ fontStyle: 'italic', fontSize: '0.8rem', color: '#4b5563', fontWeight: 700 }}>
                  AI Logistics Advisor is thinking...
                </div>
              )}
            </div>

            <form onSubmit={handleSendChat} style={{ display: 'flex', gap: '0.5rem' }}>
              <input
                type="text"
                className="search-input"
                style={{ flex: 1, padding: '0.65rem 0.85rem', fontSize: '0.85rem' }}
                placeholder="Ask AI about Choice A, B, or C..."
                value={chatInput}
                onChange={(e) => setChatInput(e.target.value)}
              />
              <button type="submit" className="btn-action" style={{ padding: '0.65rem 1rem' }} disabled={chatLoading}>
                Send
              </button>
            </form>
          </div>
        )}
      </div>
    </div>
  );
}

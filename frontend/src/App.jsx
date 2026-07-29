import React, { useState } from 'react';
import Header from './components/Header';
import MonitorTab from './components/MonitorTab';
import OutcomesTab from './components/OutcomesTab';
import Drawer from './components/Drawer';

export default function App() {
  const [activeTab, setActiveTab] = useState('monitor');
  const [selectedWarehouse, setSelectedWarehouse] = useState(null);
  const [toastMessage, setToastMessage] = useState('');

  const showToast = (msg) => {
    setToastMessage(msg);
    setTimeout(() => {
      setToastMessage('');
    }, 4000);
  };

  return (
    <div>
      <Header activeTab={activeTab} setActiveTab={setActiveTab} />

      <main className="app-main">
        {activeTab === 'monitor' && (
          <MonitorTab onSelectWarehouse={(wh) => setSelectedWarehouse(wh)} />
        )}

        {activeTab === 'outcomes' && (
          <OutcomesTab onOutcomeLogged={(msg) => showToast(msg)} />
        )}
      </main>

      <Drawer
        warehouse={selectedWarehouse}
        onClose={() => setSelectedWarehouse(null)}
        onDecisionExecuted={(msg) => showToast(msg)}
      />

      {toastMessage && <div className="toast">{toastMessage}</div>}
    </div>
  );
}

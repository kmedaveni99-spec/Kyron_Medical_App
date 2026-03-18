import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import Header from './components/Header';
import './App.css';

function App() {
  const [sessionId] = useState(() => {
    const stored = localStorage.getItem('kyron_session_id');
    if (stored) return stored;
    const id = 'sess_' + crypto.randomUUID();
    localStorage.setItem('kyron_session_id', id);
    return id;
  });

  return (
    <div className="app-container">
      <div className="app-background" />
      <div className="orb orb-1" />
      <div className="orb orb-2" />
      <div className="orb orb-3" />
      <div className="app-content">
        <Header />
        <ChatWindow sessionId={sessionId} />
      </div>
    </div>
  );
}

export default App;

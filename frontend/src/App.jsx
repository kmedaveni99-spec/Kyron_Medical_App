import { useState } from 'react';
import ChatWindow from './components/ChatWindow';
import Header from './components/Header';
import './App.css';

function generateSessionId() {
  const c = globalThis.crypto;

  if (c && typeof c.randomUUID === 'function') {
    return `sess_${c.randomUUID()}`;
  }

  if (c && typeof c.getRandomValues === 'function') {
    const bytes = c.getRandomValues(new Uint8Array(16));
    // RFC4122 v4 bits.
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, '0')).join('');
    const uuid = `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
    return `sess_${uuid}`;
  }

  return `sess_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 10)}`;
}

function App() {
  const [sessionId] = useState(() => {
    const stored = localStorage.getItem('kyron_session_id');
    if (stored) return stored;
    const id = generateSessionId();
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

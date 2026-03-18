const API_BASE = '/api';

export async function sendMessage(sessionId, message) {
  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, message }),
  });
  if (!res.ok) throw new Error('Chat request failed');
  return res.json();
}

export async function submitIntake(data) {
  const res = await fetch(`${API_BASE}/intake`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Intake submission failed');
  return res.json();
}

export async function initiateVoiceCall(sessionId, phoneNumber) {
  const res = await fetch(`${API_BASE}/voice/initiate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, phone_number: phoneNumber }),
  });
  if (!res.ok) throw new Error('Voice call initiation failed');
  return res.json();
}

export async function getOfficeInfo() {
  const res = await fetch(`${API_BASE}/office`);
  if (!res.ok) throw new Error('Failed to get office info');
  return res.json();
}

export async function getDoctors() {
  const res = await fetch(`${API_BASE}/doctors`);
  if (!res.ok) throw new Error('Failed to get doctors');
  return res.json();
}

export async function getChatHistory(sessionId) {
  const res = await fetch(`${API_BASE}/history/${sessionId}`);
  if (!res.ok) throw new Error('Failed to get history');
  return res.json();
}


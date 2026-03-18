import { getLocalMockReply } from './chatMockFallback';

const API_BASE = '/api';
const OFFLINE_QUEUE_KEY = 'kyron_offline_queue';

function queueOfflineEvent(type, payload) {
  try {
    const event = {
      id: `offline_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
      type,
      payload,
      timestamp: new Date().toISOString(),
    };
    const existing = JSON.parse(localStorage.getItem(OFFLINE_QUEUE_KEY) || '[]');
    existing.push(event);
    localStorage.setItem(OFFLINE_QUEUE_KEY, JSON.stringify(existing));
    return event.id;
  } catch {
    return null;
  }
}

async function fetchWithTimeout(url, options = {}, timeoutMs = 20000) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Request timed out. Please try again.');
    }
    throw error;
  } finally {
    clearTimeout(timeoutId);
  }
}

export async function sendMessage(sessionId, message) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, message }),
    });
    if (!res.ok) throw new Error('Chat request failed');
    return res.json();
  } catch (error) {
    return getLocalMockReply(sessionId, message, error);
  }
}

export async function submitIntake(data) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/intake`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Intake submission failed');
    return res.json();
  } catch (error) {
    const reference = queueOfflineEvent('intake_submission', data);
    return {
      success: true,
      queued: true,
      reference,
      message: 'Your details were saved in fallback mode and will be synced when service is available.',
    };
  }
}

export async function initiateVoiceCall(sessionId, phoneNumber) {
  try {
    const res = await fetchWithTimeout(`${API_BASE}/voice/initiate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, phone_number: phoneNumber }),
    });
    if (!res.ok) throw new Error('Voice call initiation failed');
    return res.json();
  } catch (error) {
    const reference = queueOfflineEvent('voice_request', { sessionId, phoneNumber });
    return {
      success: true,
      queued: true,
      reference,
      message: 'Your callback request is saved in fallback mode. We will follow up shortly.',
    };
  }
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


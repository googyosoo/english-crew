const API_BASE = 'http://127.0.0.1:8765';

export async function fetchHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return { status: 'error', gemini: 'missing_key', model: '오프라인' };
  }
}

export async function fetchChannels() {
  const res = await fetch(`${API_BASE}/channels`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchBots() {
  const res = await fetch(`${API_BASE}/bots`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchMessages(channelId) {
  const res = await fetch(`${API_BASE}/channels/${channelId}/messages`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendRequest(channelId, content) {
  const res = await fetch(`${API_BASE}/channels/${channelId}/requests`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ content }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function decideApproval(approvalId, decision, reason = '') {
  const res = await fetch(`${API_BASE}/approvals/${approvalId}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ decision, reason }),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchTaskDeliverable(taskId) {
  const res = await fetch(`${API_BASE}/tasks/${taskId}/deliverable`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export function subscribeToRequestEvents(requestId, onEvent, onError) {
  const url = `${API_BASE}/requests/${requestId}/events`;
  const eventSource = new EventSource(url);

  eventSource.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data);
      if (onEvent) onEvent(data);
    } catch (e) {
      console.error('Failed to parse SSE event:', e);
    }
  };

  eventSource.onerror = (err) => {
    eventSource.close();
    if (onError) onError(err);
  };

  return () => {
    eventSource.close();
  };
}

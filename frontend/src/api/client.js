// API Client with Dynamic Port and Token Authentication (Phase 4-3b Security)

export function getApiBase() {
  if (typeof window !== 'undefined' && window.electronAPI && typeof window.electronAPI.getApiUrl === 'function') {
    return window.electronAPI.getApiUrl();
  }
  if (typeof window !== 'undefined' && window.location && window.location.origin && window.location.origin.startsWith('http')) {
    return window.location.origin;
  }
  return 'http://127.0.0.1:8765';
}

export function getApiToken() {
  if (typeof window !== 'undefined' && window.electronAPI && typeof window.electronAPI.getToken === 'function') {
    return window.electronAPI.getToken();
  }
  return '';
}

async function authFetch(endpoint, options = {}) {
  const base = getApiBase();
  const token = getApiToken();
  const headers = { ...options.headers };

  if (token) {
    headers['X-Crew-Token'] = token;
  }

  const res = await fetch(`${base}${endpoint}`, {
    ...options,
    headers,
  });

  return res;
}

export async function fetchHealth() {
  try {
    const res = await authFetch('/health');
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    return { status: 'error', gemini: 'missing_key', model: '오프라인' };
  }
}

export async function fetchChannels() {
  const res = await authFetch('/channels');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchBots() {
  const res = await authFetch('/bots');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchMessages(channelId) {
  const res = await authFetch(`/channels/${channelId}/messages`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function sendRequest(channelId, content) {
  const res = await authFetch(`/channels/${channelId}/requests`, {
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
  const res = await authFetch(`/approvals/${approvalId}`, {
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
  const res = await authFetch(`/tasks/${taskId}/deliverable`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchChannelContext(channelId, unit = '') {
  const url = unit
    ? `/channels/${channelId}/context?unit=${encodeURIComponent(unit)}`
    : `/channels/${channelId}/context`;
  const res = await authFetch(url);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function saveChannelContext(channelId, noteData) {
  const res = await authFetch(`/channels/${channelId}/context`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(noteData),
  });
  if (!res.ok) {
    const errData = await res.json().catch(() => ({}));
    throw new Error(errData.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function deleteChannelContext(noteId) {
  const res = await authFetch(`/context/${noteId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export function getExportUrl(requestId, format = 'docx') {
  const base = getApiBase();
  const token = getApiToken();
  const tokenParam = token ? `&token=${encodeURIComponent(token)}` : '';
  return `${base}/requests/${requestId}/export?format=${format}${tokenParam}`;
}

export async function fetchExportDir() {
  const res = await authFetch('/settings/export_dir');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function saveExportDir(exportDir) {
  const res = await authFetch('/settings/export_dir', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ export_dir: exportDir }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function fetchRoutines() {
  const res = await authFetch('/routines');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function createRoutine(routineData) {
  const res = await authFetch('/routines', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(routineData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function updateRoutine(routineId, updateData) {
  const res = await authFetch(`/routines/${routineId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updateData),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function deleteRoutine(routineId) {
  const res = await authFetch(`/routines/${routineId}`, {
    method: 'DELETE',
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function runRoutineNow(routineId) {
  const res = await authFetch(`/routines/${routineId}/run`, {
    method: 'POST',
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export async function fetchApiKeyStatus() {
  const res = await authFetch('/settings/api_key');
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return await res.json();
}

export async function saveApiKey(apiKey, model = null) {
  const res = await authFetch('/settings/api_key', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey, model }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return await res.json();
}

export function subscribeToRequestEvents(requestId, onEvent, onError) {
  const base = getApiBase();
  const token = getApiToken();
  const url = token
    ? `${base}/requests/${requestId}/events?token=${encodeURIComponent(token)}`
    : `${base}/requests/${requestId}/events`;

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

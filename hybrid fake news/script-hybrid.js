const API_BASE_URL = (() => {
  const queryApi = new URLSearchParams(window.location.search).get('api');
  if (queryApi) {
    return queryApi.replace(/\/$/, '');
  }

  if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
    return `http://${window.location.hostname}:8002`;
  }

  return 'http://127.0.0.1:8002';
})();

const textEl = document.getElementById('text');
const academicEl = document.getElementById('academic');
const analyzeBtn = document.getElementById('analyzeBtn');
const statusEl = document.getElementById('status');
const verdictEl = document.getElementById('verdict');
const rawEl = document.getElementById('raw');

function labelClassFromLabel(label, consensus) {
  const c = (consensus || '').toLowerCase();
  if (c.includes('not credible')) return 'fake';
  if (c.includes('credible')) return 'real';
  if (c.includes('unverifiable')) return 'uncertain';

  const l = (label || '').toLowerCase();
  if (l.includes('fake')) return 'fake';
  if (l.includes('real') || l.includes('credible')) return 'real';
  return 'uncertain';
}

async function analyze() {
  const text = textEl.value.trim();
  if (text.length < 20) {
    alert('Please paste at least 20 characters.');
    return;
  }

  const endpoint = academicEl.checked ? '/detect-academic' : '/detect';
  statusEl.textContent = `Calling ${API_BASE_URL}${endpoint} ...`;
  verdictEl.style.display = 'none';
  rawEl.textContent = '';

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || `API error ${response.status}`);
    }

    rawEl.textContent = JSON.stringify(data, null, 2);

    const label = data.prediction || (data.lstm && data.lstm.label) || 'UNKNOWN';
    const confidence = data.confidence ?? (data.lstm && data.lstm.confidence) ?? 0;
    const consensus = data.consensus || 'n/a';
    const badgeClass = labelClassFromLabel(label, consensus);

    verdictEl.innerHTML = `
      <div style="display:flex; align-items:center; gap:12px;">
        <span class="badge ${badgeClass}">● ${label}</span>
        <span class="muted">Consensus: ${consensus}</span>
      </div>
      <div style="flex:1; max-width: 420px;">
        <div class="bar"><i style="width:${Math.round(confidence * 100)}%"></i></div>
        <div class="muted" style="font-size:12px; margin-top:4px;">
          Confidence: ${(confidence * 100).toFixed(1)}%
        </div>
      </div>
    `;
    verdictEl.style.display = 'flex';

    statusEl.textContent = 'Done.';
  } catch (error) {
    const message =
      error instanceof TypeError
        ? `Network/CORS error. Ensure backend is running at ${API_BASE_URL}, and your page origin is allowed by backend CORS.`
        : error.message;
    statusEl.textContent = `Error: ${message}`;
    rawEl.textContent = String(error);
  }
}

analyzeBtn.addEventListener('click', analyze);

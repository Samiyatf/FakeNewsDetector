const TARGETS = [
  { name: 'LSTM Test Backend', base: 'http://127.0.0.1:8000' },
  { name: 'Transformer Backend', base: 'http://127.0.0.1:8001' },
  { name: 'Hybrid Backend', base: 'http://127.0.0.1:8002' },
];

const textEl = document.getElementById('text');
const academicEl = document.getElementById('academic');
const analyzeBtn = document.getElementById('analyzeBtn');
const statusEl = document.getElementById('status');
const tableEl = document.getElementById('resultsTable');
const resultsBodyEl = document.getElementById('resultsBody');
const rawEl = document.getElementById('raw');

function getLabel(data) {
  if (data.prediction) return data.prediction;
  if (data.lstm && data.lstm.label) return data.lstm.label;
  return 'UNKNOWN';
}

function getConfidencePct(data) {
  const conf = (data.confidence ?? (data.lstm && data.lstm.confidence) ?? 0);
  return Math.max(0, Math.min(100, Math.round(conf * 1000) / 10));
}

function getConsensus(data) {
  return data.consensus || 'n/a';
}

function getSource(data) {
  if (data.hybrid && data.hybrid.source) return data.hybrid.source;
  return data.model_used || 'n/a';
}

function barHtml(pct) {
  return `<div class="bar-wrap"><div class="bar-mini"><i style="width:${pct}%"></i></div></div>`;
}

async function fetchOne(target, endpoint, payload) {
  try {
    const response = await fetch(`${target.base}${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.detail || `HTTP ${response.status}`);
    }

    const pct = getConfidencePct(data);
    return {
      backend: target.name,
      label: getLabel(data),
      confidence: `${pct}%`,
      consensus: getConsensus(data),
      source: getSource(data),
      bar: barHtml(pct),
      status: 'OK',
      statusClass: 'status-ok',
      raw: data,
    };
  } catch (error) {
    return {
      backend: target.name,
      label: 'ERROR',
      confidence: '0%',
      consensus: 'n/a',
      source: 'n/a',
      bar: barHtml(0),
      status: error.message,
      statusClass: 'status-err',
      raw: { error: error.message },
    };
  }
}

function renderRows(rows) {
  resultsBodyEl.innerHTML = rows.map((row) => `
    <tr>
      <td>${row.backend}</td>
      <td>${row.label}</td>
      <td>${row.confidence}</td>
      <td>${row.consensus}</td>
      <td>${row.source}</td>
      <td>${row.bar}</td>
      <td class="${row.statusClass}">${row.status}</td>
    </tr>
  `).join('');

  tableEl.style.display = 'table';
}

async function runComparison() {
  const text = textEl.value.trim();
  if (text.length < 20) {
    alert('Please paste at least 20 characters.');
    return;
  }

  const endpoint = academicEl.checked ? '/detect-academic' : '/detect';
  statusEl.textContent = `Running ${endpoint} across all 3 backends...`;
  rawEl.textContent = '';

  const rows = await Promise.all(TARGETS.map((target) => fetchOne(target, endpoint, { text })));
  renderRows(rows);
  rawEl.textContent = JSON.stringify(rows.map((r) => ({ backend: r.backend, raw: r.raw })), null, 2);

  statusEl.textContent = 'Comparison complete.';
}

analyzeBtn.addEventListener('click', runComparison);

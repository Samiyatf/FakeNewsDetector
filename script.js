// --- Tab switcher
function setTab(which) {
  const tabUrl = document.getElementById('tab-url');
  const tabText = document.getElementById('tab-text');
  const inpUrl = document.getElementById('input-url');
  const inpText = document.getElementById('input-text');
  const sel = which === 'url';

  tabUrl.classList.toggle('active', sel);
  tabText.classList.toggle('active', !sel);

  tabUrl.setAttribute('aria-selected', sel);
  tabText.setAttribute('aria-selected', !sel);

  inpUrl.style.display = sel ? 'block' : 'none';
  inpText.style.display = sel ? 'none' : 'block';
}

let lastResult = null;

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

// --- Main analyze function with real API call
async function analyze() {
  const steps = document.getElementById('steps');
  const verdict = document.getElementById('verdict');
  const explain = document.getElementById('explain');

  // Get input text
  const isUrlMode = document.getElementById('tab-url').classList.contains('active');
  let textToAnalyze = '';
  
  if (isUrlMode) {
    const urlInput = document.getElementById('url').value.trim();
    if (!urlInput) {
      alert('Please enter a URL');
      return;
    }
    // Note: URL scraping would require additional backend support
    alert('URL scraping is not yet implemented. Please use "Paste Text" mode for now.');
    return;
  } else {
    textToAnalyze = document.getElementById('text').value.trim();
    if (!textToAnalyze) {
      alert('Please paste some text to analyze');
      return;
    }
    if (textToAnalyze.length < 20) {
      alert('Please paste a longer text (at least 20 characters)');
      return;
    }
  }

  steps.style.display = 'flex';
  verdict.style.display = 'none';
  explain.style.display = 'none';

  steps.innerHTML = '';

  const s1 = addStep('Tokenizing…');
  const s2 = addStep('Model scoring…');
  const s3 = addStep('Analyzing content…');

  setTimeout(() => markDone(s1), 300);
  setTimeout(() => markActive(s2), 300);

  try {
    const academicMode = document.getElementById('academic').checked;
    const endpoint = academicMode ? '/detect-academic' : '/detect';

    // Make API call
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ text: textToAnalyze })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(errorData.detail || `API error: ${response.status}`);
    }

    const data = await response.json();
    
    setTimeout(() => {
      markDone(s2);
      markActive(s3);
    }, 600);

    setTimeout(() => {
      markDone(s3);
      lastResult = data;
      renderResult(data);
    }, 1200);

  } catch (error) {
    console.error('Analysis error:', error);
    steps.innerHTML = '';
    alert(`Analysis failed: ${error.message}\n\nMake sure the backend server is running at ${API_BASE_URL}`);
  }
}

function addStep(label) {
  const steps = document.getElementById('steps');
  const el = document.createElement('div');
  el.className = 'step active';
  el.innerHTML = `<span>⏳</span> ${label}`;
  steps.appendChild(el);
  return el;
}

function markActive(el) {
  el.classList.add('active');
}

function markDone(el) {
  el.classList.remove('active');
  el.classList.add('done');
  el.innerHTML = el.innerHTML.replace('⏳', '✅');
}

// --- Render results
function renderResult(data) {
  const verdict = document.getElementById('verdict');
  const explain = document.getElementById('explain');

  verdict.style.display = 'flex';
  explain.style.display = 'grid';

  const isAcademic = data && data.mode === 'academic';

  if (isAcademic) {
    const labelClass =
      data.consensus === 'Not credible'
        ? 'fake'
        : data.consensus === 'Credible'
        ? 'real'
        : 'uncertain';
    const badgeText = data.consensus || data.prediction || 'Unverifiable / insufficient evidence';
    const confidence = Number(data.confidence || 0);

    verdict.innerHTML = `
      <div style="display:flex; align-items:center; gap:12px;">
        <span class="badge ${labelClass}">● ${badgeText}</span>
        <span class="muted">Mode: academic</span>
      </div>
      <div style="flex:1; max-width: 420px;">
        <div class="bar"><i style="width:${Math.round(confidence * 100)}%"></i></div>
        <div class="muted" style="font-size:12px; margin-top:4px;">
          Confidence: ${(confidence * 100).toFixed(1)}%
        </div>
      </div>
    `;

    const claimsList = (data.claims || []).map((c) => `<li>${c}</li>`).join('');
    const limitationsList = (data.limitations || [])
      .map((l) => `<li>${l}</li>`)
      .join('');
    const evidenceBlocks = (data.evidence_prompts || [])
      .map(
        (item) => `
          <div style="margin-top:8px;">
            <div class="muted" style="margin-bottom:6px;">${item.claim}</div>
            <ul class="muted">
              ${(item.questions || []).map((q) => `<li>${q}</li>`).join('')}
            </ul>
          </div>
        `
      )
      .join('');

    explain.innerHTML = `
      <details open>
        <summary>Claims to verify</summary>
        <ul style="margin-top:8px;">${claimsList}</ul>
      </details>

      <details>
        <summary>Evidence prompts</summary>
        ${evidenceBlocks || '<div class="muted" style="margin-top:8px;">No prompts available.</div>'}
      </details>

      <details>
        <summary>Limitations</summary>
        <ul class="muted" style="margin-top:8px;">${limitationsList}</ul>
      </details>
    `;

    document.getElementById('lstmCard').textContent = JSON.stringify(
      {
        mode: data.mode,
        prediction: data.prediction,
        confidence: data.confidence,
        chunk_scores: data.chunk_scores,
      },
      null,
      2
    );

    document.getElementById('llmCard').textContent = JSON.stringify(
      {
        claims: data.claims,
        evidence_prompts: data.evidence_prompts,
        limitations: data.limitations,
      },
      null,
      2
    );
    return;
  }

  const labelClass =
    data.consensus === 'Not credible'
      ? 'fake'
      : data.consensus === 'Credible'
      ? 'real'
      : 'uncertain';

  const badgeText = data.consensus || 'Unverifiable / insufficient evidence';

  verdict.innerHTML = `
    <div style="display:flex; align-items:center; gap:12px;">
      <span class="badge ${labelClass}">● ${badgeText}</span>
      <span class="muted">Consensus: ${data.consensus}</span>
    </div>
    <div style="flex:1; max-width: 420px;">
      <div class="bar"><i style="width:${Math.round(data.lstm.confidence*100)}%"></i></div>
      <div class="muted" style="font-size:12px; margin-top:4px;">
        Confidence (LSTM): ${(data.lstm.confidence * 100).toFixed(1)}%
      </div>
    </div>
  `;

  const signalsChips = data.lstm.signals
    .map(
      (s) =>
        `<span class="chip" title="impact ${(s.impact * 100).toFixed(0)}%">${s.text}</span>`
    )
    .join('');

  const claimsList = data.llm.claims.map((c) => `<li>${c}</li>`).join('');
  const rationaleList = data.llm.rationale
    .map((r) => `<li>${r}</li>`)
    .join('');

  explain.innerHTML = `
    <details open>
      <summary>Content signals (LSTM)</summary>
      <div class="chips" style="margin-top:8px;">
        ${signalsChips || '<span class="muted">No notable cues detected.</span>'}
      </div>
    </details>

    <details>
      <summary>LLM explanation</summary>
      <ul class="muted" style="margin-top:8px;">${rationaleList}</ul>
    </details>

    <details>
      <summary>Claims to double-check</summary>
      <ul style="margin-top:8px;">${claimsList}</ul>
    </details>
  `;

  document.getElementById('lstmCard').textContent = JSON.stringify(
    {
      label: data.lstm.label,
      confidence: data.lstm.confidence,
      top_tokens: data.lstm.signals.map((s) => s.text),
    },
    null,
    2
  );

  document.getElementById('llmCard').textContent = JSON.stringify(
    {
      label: data.llm.label,
      rationale: data.llm.rationale,
    },
    null,
    2
  );
}

function openDrawer() {
  document.getElementById('drawer').classList.add('open');
  document.getElementById('drawer').setAttribute('aria-hidden', 'false');
}

function closeDrawer() {
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('drawer').setAttribute('aria-hidden', 'true');
}

// Export JSON
function exportJSON() {
  if (!lastResult) {
    alert('Run an analysis first.');
    return;
  }

  const blob = new Blob([JSON.stringify(lastResult, null, 2)], {
    type: 'application/json',
  });

  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');

  a.href = url;
  a.download = 'analysis-result.json';
  a.click();

  URL.revokeObjectURL(url);
}

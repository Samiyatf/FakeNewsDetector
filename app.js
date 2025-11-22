// app.js
// Front-end logic for Fake News Detector prototype.
// Note: currently uses mockResult() with hard-coded data.
// In the final version, analyze() will call a backend API instead. 

// --- Demo analysis flow (mocked). Replace with a real fetch later.
let lastResult = null;

function analyze() {
  // Grab and clean the pasted article text
  const textValue = document.getElementById('text').value.trim();

  // ---------------------------
  // INPUT VALIDATION
  // ---------------------------

  if (!textValue) {
    alert("Please paste an article before analyzing.");
    return;
  }

  if (textValue.length < 20) {
    alert("The article text is too short to analyze. Please add more content.");
    return;
  }

  const steps = document.getElementById('steps');
  const verdict = document.getElementById('verdict');
  const explain = document.getElementById('explain');

  steps.style.display = 'flex';
  verdict.style.display = 'none';
  explain.style.display = 'none';
  steps.innerHTML = '';

  // Step visuals
  const s1 = addStep('Tokenizing…');
  const s2 = addStep('LSTM scoring…');
  const s3 = addStep('LLM review…');

  // Simulate timings
  setTimeout(() => { markDone(s1); }, 500);
  setTimeout(() => { markActive(s2); }, 500);
  setTimeout(() => { markDone(s2); markActive(s3); }, 1200);
  setTimeout(() => {
    markDone(s3);
    // Produce mock data (you can tweak to demo each verdict)
    lastResult = mockResult();
    renderResult(lastResult);
  }, 2100);
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

function renderResult(data) {
  const verdict = document.getElementById('verdict');
  const explain = document.getElementById('explain');
  verdict.style.display = 'flex';
  explain.style.display = 'grid';

  // Badge + confidence
  const labelClass = data.consensus === 'disagree'
    ? 'uncertain'
    : data.lstm.label.toLowerCase();
  const badgeText = data.consensus === 'disagree'
    ? 'UNCERTAIN (disagree)'
    : data.lstm.label;

  verdict.innerHTML = `
    <div style="display:flex; align-items:center; gap:12px;">
      <span class="badge ${labelClass}">● ${badgeText}</span>
      <span class="muted">Consensus: ${data.consensus}</span>
    </div>
    <div style="flex:1; max-width: 420px;">
      <div class="bar"><i style="width:${Math.round(data.lstm.confidence * 100)}%"></i></div>
      <div class="muted" style="font-size:12px; margin-top:4px;">
        Confidence (LSTM): ${(data.lstm.confidence * 100).toFixed(1)}%
      </div>
    </div>
  `;

  // Why panels
  const signalsChips = data.lstm.signals
    .map(s => `<span class="chip" title="impact ${(s.impact * 100).toFixed(0)}%">${s.text}</span>`)
    .join('');

  const claimsList = data.llm.claims
    .map(c => `<li>${c}</li>`)
    .join('');

  const rationaleList = data.llm.rationale
    .map(r => `<li>${r}</li>`)
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

  // Fill drawer cards
  document.getElementById('lstmCard').textContent = JSON.stringify(
    {
      label: data.lstm.label,
      confidence: data.lstm.confidence,
      top_tokens: data.lstm.signals.map(s => s.text)
    },
    null,
    2
  );

  document.getElementById('llmCard').textContent = JSON.stringify(
    {
      label: data.llm.label,
      rationale: data.llm.rationale
    },
    null,
    2
  );
}

function mockResult() {
  // Three presets; rotate for variety
  const presets = [
    {
      lstm: {
        label: 'FAKE',
        confidence: 0.86,
        signals: [
          { type: 'phrase', text: 'BREAKING', impact: 0.18 },
          { type: 'style', text: 'ALL-CAPS headline', impact: 0.12 },
          { type: 'phrase', text: 'shocking truth', impact: 0.09 }
        ]
      },
      llm: {
        ran: true,
        label: 'UNCERTAIN',
        rationale: [
          'The article uses sensational language and lacks primary sources.',
          'Quotes are unattributed; claims reference a single blog.',
          'Author bio is missing and publication is opaque.'
        ],
        claims: [
          '“Agency confirmed X on Friday.”',
          '“Study with 50,000 participants found Y.”',
          '“CEO admitted Z on live TV.”'
        ]
      },
      consensus: 'disagree',
      meta: { domain: 'rumor-news.example', byline: false }
    },
    {
      lstm: {
        label: 'REAL',
        confidence: 0.78,
        signals: [
          { type: 'style', text: 'neutral tone', impact: 0.11 },
          { type: 'structure', text: 'attributed quotes', impact: 0.08 }
        ]
      },
      llm: {
        ran: true,
        label: 'REAL',
        rationale: [
          'Multiple independent sources are cited and linked.',
          'Contains direct quotes with names and roles.',
          'Data source is a public report with publication date.'
        ],
        claims: ['“Report released on April 4, 2025.”']
      },
      consensus: 'agree',
      meta: { domain: 'major-outlet.example', byline: true }
    },
    {
      lstm: {
        label: 'UNCERTAIN',
        confidence: 0.55,
        signals: [
          { type: 'phrase', text: 'experts say', impact: 0.06 }
        ]
      },
      llm: {
        ran: true,
        label: 'UNCERTAIN',
        rationale: [
          'Insufficient detail to verify; references are generic.',
          'Key numbers are rounded with no links.'
        ],
        claims: ['“Experts estimate losses of $10B.”']
      },
      consensus: 'agree',
      meta: { domain: 'opinion-blog.example', byline: true }
    }
  ];

  const pick = presets[Math.floor(Math.random() * presets.length)];

  // Academic mode nudges toward UNCERTAIN 
  if (document.getElementById('academic').checked && pick.lstm.label === 'REAL') {
    pick.lstm.confidence = Math.max(0.58, pick.lstm.confidence - 0.15);
  }

  return pick;
}

function openDrawer() {
  document.getElementById('drawer').classList.add('open');
  document.getElementById('drawer').setAttribute('aria-hidden', 'false');
}

function closeDrawer() {
  document.getElementById('drawer').classList.remove('open');
  document.getElementById('drawer').setAttribute('aria-hidden', 'true');
}

function exportJSON() {
  if (!lastResult) {
    alert('Run an analysis first.');
    return;
  }
  const blob = new Blob([JSON.stringify(lastResult, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = 'analysis-result.json';
  a.click();
  URL.revokeObjectURL(url);
}

// --- Optional: hook up to a real backend later
// Replace mockResult() call with something like:
//
// fetch('/api/analyze', {
//   method: 'POST',
//   headers: { 'Content-Type': 'application/json' },
//   body: JSON.stringify({
//     input: { type: 'text', value: document.getElementById('text').value },
//     options: { run_llm: true }
//   })
// })
//   .then(r => r.json())
//   .then(renderResult);

/**
 * TCS NQT 2026 – Exam Engine
 * Handles: Security, Timer, Question Navigation, Auto-save, Anti-cheat
 */

'use strict';

// ══════════════════════════════════════════════
// GLOBAL STATE
// ══════════════════════════════════════════════

const STATE = {
  sections: SECTIONS,               // from template
  currentSectionIdx: 0,
  currentQIdx: 0,
  questions: {},                    // { section_id: [] }
  answers:   {},                    // { q_id: answer }
  status:    {},                    // { q_id: 'answered'|'not-answered'|'marked'|'not-visited' }
  timers:    {},                    // { section_id: secondsRemaining }
  activeTimer: null,
  violationCount: 0,
  autoSubmitted: false,
  cameraStream: null,
};

const LS_PREFIX = 'tcs_nqt_';
const currentSection = () => STATE.sections[STATE.currentSectionIdx];

// ══════════════════════════════════════════════
// SECURITY: Anti-Cheat
// ══════════════════════════════════════════════

function initSecurity() {
  // Disable right-click
  document.addEventListener('contextmenu', e => e.preventDefault());

  // Disable copy/paste/cut/select
  ['copy','paste','cut','selectstart'].forEach(ev =>
    document.addEventListener(ev, e => e.preventDefault())
  );

  // Disable keyboard shortcuts
  document.addEventListener('keydown', e => {
    // F12, Ctrl+Shift+I, Ctrl+Shift+J, Ctrl+U
    if (e.key === 'F12') { e.preventDefault(); return; }
    if (e.ctrlKey && e.shiftKey && ['I','J','C'].includes(e.key)) { e.preventDefault(); return; }
    if (e.ctrlKey && ['c','v','x','a','u','s'].includes(e.key.toLowerCase())) { e.preventDefault(); return; }
    if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) { e.preventDefault(); return; } // prevent refresh
  });

  // Tab switch / window blur detection
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'hidden') handleViolation('Tab switch detected');
  });

  window.addEventListener('blur', () => {
    if (!STATE.autoSubmitted) handleViolation('Window focus lost');
  });

  // Fullscreen exit detection
  document.addEventListener('fullscreenchange', () => {
    if (!document.fullscreenElement && !STATE.autoSubmitted) {
      handleViolation('Fullscreen exit detected');
    }
  });

  // Prevent back button
  history.pushState(null, null, window.location.href);
  window.addEventListener('popstate', () => {
    history.pushState(null, null, window.location.href);
  });

  // Online/offline
  window.addEventListener('offline', () => {
    document.getElementById('offlineBanner').classList.remove('hidden');
  });
  window.addEventListener('online', () => {
    document.getElementById('offlineBanner').classList.add('hidden');
  });

  // Prevent dev-tools resize trick
  const devToolsCheck = () => {
    const threshold = 160;
    if (window.outerWidth - window.innerWidth > threshold ||
        window.outerHeight - window.innerHeight > threshold) {
      // soft warning only – don't block legitimate smaller windows
    }
  };
  setInterval(devToolsCheck, 3000);
}

async function handleViolation(reason) {
  if (STATE.autoSubmitted) return;

  // Debounce – ignore rapid-fire events
  if (STATE._violationCooldown) return;
  STATE._violationCooldown = true;
  setTimeout(() => { STATE._violationCooldown = false; }, 3000);

  try {
    const res  = await fetch('/api/violation', { method:'POST', headers:{'Content-Type':'application/json'}, body:'{}' });
    const data = await res.json();
    STATE.violationCount = data.violation_count;

    if (data.auto_submitted) {
      STATE.autoSubmitted = true;
      clearInterval(STATE.activeTimer);
      document.getElementById('autoSubmitOverlay').classList.remove('hidden');
    } else {
      // Show warning
      const overlay = document.getElementById('violationOverlay');
      document.getElementById('violationMsg').textContent = reason + '. Tab switching and fullscreen exit are not allowed.';
      document.getElementById('violationCount').textContent = `Warning ${data.violation_count}/2`;
      overlay.classList.remove('hidden');

      // Show persistent warning banner
      document.getElementById('warnBanner').classList.remove('hidden');
    }
  } catch(e) {
    console.warn('Violation log failed', e);
  }
}

function dismissViolation() {
  document.getElementById('violationOverlay').classList.add('hidden');
  // Re-request fullscreen after dismissal
  if (!document.fullscreenElement) {
    document.documentElement.requestFullscreen().catch(() => {});
  }
}

// ══════════════════════════════════════════════
// CAMERA
// ══════════════════════════════════════════════

async function initCamera() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video:true, audio:true });
    STATE.cameraStream = stream;
    const vid = document.getElementById('headerCam');
    vid.srcObject = stream;
    vid.style.display = 'block';
  } catch(e) {
    // Camera unavailable – show placeholder
    const mon = document.querySelector('.cam-monitor');
    if (mon) {
      mon.innerHTML = '<div style="height:70px;display:flex;align-items:center;justify-content:center;color:#8a99b3;font-size:9px;text-align:center;padding:4px">Camera<br>unavailable</div><div class="cam-label"><span class="dot-blink"></span>Monitoring</div>';
    }
  }
}

// ══════════════════════════════════════════════
// TIMER SYSTEM
// ══════════════════════════════════════════════

function initTimers() {
  STATE.sections.forEach(s => {
    const lsKey = LS_PREFIX + 'timer_' + s.id;
    const saved = localStorage.getItem(lsKey);
    STATE.timers[s.id] = saved !== null ? parseInt(saved, 10) : s.time * 60;
  });
}

function startSectionTimer(sectionId) {
  clearInterval(STATE.activeTimer);

  const totalSecs = STATE.sections.find(s => s.id === sectionId).time * 60;
  const bar       = document.getElementById('timerBar');
  const display   = document.getElementById('timerDisplay');
  const label     = document.getElementById('timerSectionName');
  const secName   = STATE.sections.find(s => s.id === sectionId).name;

  label.textContent = secName;

  function tick() {
    const secs = STATE.timers[sectionId];
    if (secs <= 0) {
      clearInterval(STATE.activeTimer);
      localStorage.removeItem(LS_PREFIX + 'timer_' + sectionId);
      display.textContent = '00:00';
      onSectionTimeUp();
      return;
    }

    const m = String(Math.floor(secs / 60)).padStart(2, '0');
    const s = String(secs % 60).padStart(2, '0');
    display.textContent = m + ':' + s;

    // Color coding
    const pct = secs / totalSecs;
    bar.style.width = (pct * 100) + '%';
    if (pct <= 0.1) {
      display.className = 'timer-display urgent';
      bar.className = 'timer-bar urgent';
    } else if (pct <= 0.25) {
      display.className = 'timer-display warn';
      bar.className = 'timer-bar warn';
    } else {
      display.className = 'timer-display';
      bar.className = 'timer-bar';
    }

    STATE.timers[sectionId]--;
    localStorage.setItem(LS_PREFIX + 'timer_' + sectionId, STATE.timers[sectionId]);
  }

  tick();
  STATE.activeTimer = setInterval(tick, 1000);
}

async function onSectionTimeUp() {
  const idx = STATE.currentSectionIdx;
  if (idx < STATE.sections.length - 1) {
    // Move to next section
    STATE.currentSectionIdx++;
    STATE.currentQIdx = 0;
    await loadSection(currentSection().id);
    updateSectionProgressBar();
    startSectionTimer(currentSection().id);
  } else {
    // Last section – auto submit
    await doFinalSubmit(true);
  }
}

// ══════════════════════════════════════════════
// QUESTION LOADING
// ══════════════════════════════════════════════

async function loadSection(sectionId) {
  if (STATE.questions[sectionId]) {
    renderQuestion();
    renderPalette();
    return;
  }

  // Show loading
  document.getElementById('loadingSpinner').classList.remove('hidden');
  document.getElementById('questionContent').classList.add('hidden');

  try {
    const res  = await fetch('/api/questions/' + sectionId);
    const data = await res.json();
    STATE.questions[sectionId] = data;

    // Restore saved answers
    data.forEach(q => {
      if (q.saved_answer) {
        STATE.answers[q.id]  = q.saved_answer;
        STATE.status[q.id]   = 'answered';
      } else if (!STATE.status[q.id]) {
        STATE.status[q.id]   = 'not-visited';
      }
    });

    document.getElementById('loadingSpinner').classList.add('hidden');
    document.getElementById('questionContent').classList.remove('hidden');

    renderQuestion();
    renderPalette();
  } catch(e) {
    document.getElementById('loadingSpinner').innerHTML = '<div style="color:#ef4444">Failed to load questions. Please refresh.</div>';
  }
}

// ══════════════════════════════════════════════
// RENDER QUESTION
// ══════════════════════════════════════════════

function renderQuestion() {
  const sec = currentSection();
  const qs  = STATE.questions[sec.id];
  if (!qs || !qs.length) return;

  const q    = qs[STATE.currentQIdx];
  const qNum = STATE.currentQIdx + 1;

  // Header meta
  document.getElementById('secTag').textContent  = sec.name;
  document.getElementById('secQnum').textContent = `Question ${qNum} of ${qs.length}`;

  // Question text
  document.getElementById('questionText').textContent = q.question_text || '';

  // Image
  const imgWrap = document.getElementById('questionImgWrap');
  if (q.question_image_path) {
    document.getElementById('questionImg').src = '/static/' + q.question_image_path;
    imgWrap.classList.remove('hidden');
  } else {
    imgWrap.classList.add('hidden');
  }

  // Options
  const isFill = q.question_type === 'fill';
  document.getElementById('mcqOptions').classList.toggle('hidden', isFill);
  document.getElementById('fillOptions').classList.toggle('hidden', !isFill);

  if (!isFill) {
    document.getElementById('optTextA').textContent = q.option_a || '';
    document.getElementById('optTextB').textContent = q.option_b || '';
    document.getElementById('optTextC').textContent = q.option_c || '';
    document.getElementById('optTextD').textContent = q.option_d || '';

    // Restore selection
    const saved = STATE.answers[q.id] || '';
    document.querySelectorAll('.option-label').forEach(el => {
      el.classList.remove('selected');
      const val = el.querySelector('input').value;
      if (val === saved) el.classList.add('selected');
    });

    // Click handlers
    document.querySelectorAll('.option-label').forEach(el => {
      el.onclick = () => selectOption(el, q);
    });
  } else {
    const fi = document.getElementById('fillInput');
    fi.value = STATE.answers[q.id] || '';
    fi.oninput = () => {
      STATE.answers[q.id] = fi.value.trim();
      STATE.status[q.id]  = fi.value.trim() ? 'answered' : 'not-answered';
      updatePaletteBtn(q.id);
      updateStats();
      saveAnswerDebounced(q.id, fi.value.trim());
    };
  }

  // Mark visited if not-visited
  if (STATE.status[q.id] === 'not-visited') {
    STATE.status[q.id] = 'not-answered';
    updatePaletteBtn(q.id);
  }

  // Update palette current highlight
  updatePaletteCurrent();
  updateStats();
  updateNavBtns();
}

function selectOption(el, q) {
  document.querySelectorAll('.option-label').forEach(l => l.classList.remove('selected'));
  el.classList.add('selected');
  const val = el.querySelector('input').value;
  STATE.answers[q.id] = val;
  STATE.status[q.id]  = 'answered';
  updatePaletteBtn(q.id);
  updateStats();
  saveAnswer(q.id, val);
}

// ══════════════════════════════════════════════
// PALETTE
// ══════════════════════════════════════════════

function renderPalette() {
  const sec  = currentSection();
  const qs   = STATE.questions[sec.id] || [];
  const grid = document.getElementById('paletteGrid');
  grid.innerHTML = '';

  qs.forEach((q, idx) => {
    const btn = document.createElement('button');
    btn.className = 'pal-btn';
    btn.textContent = idx + 1;
    btn.id = 'pal_' + q.id;
    btn.onclick = () => {
      STATE.currentQIdx = idx;
      renderQuestion();
    };
    applyPaletteClass(btn, q.id);
    grid.appendChild(btn);
  });

  updatePaletteCurrent();
  updateStats();
}

function applyPaletteClass(btn, qId) {
  btn.className = 'pal-btn';
  const st = STATE.status[qId];
  if (st === 'answered')     btn.classList.add('answered');
  else if (st === 'marked')  btn.classList.add('marked');
  else if (st === 'not-answered') btn.classList.add('not-answered');
}

function updatePaletteBtn(qId) {
  const btn = document.getElementById('pal_' + qId);
  if (btn) applyPaletteClass(btn, qId);
}

function updatePaletteCurrent() {
  document.querySelectorAll('.pal-btn').forEach(b => b.classList.remove('current'));
  const qs = STATE.questions[currentSection().id] || [];
  const q  = qs[STATE.currentQIdx];
  if (q) {
    const btn = document.getElementById('pal_' + q.id);
    if (btn) btn.classList.add('current');
  }
}

function updateStats() {
  const qs = STATE.questions[currentSection().id] || [];
  let ans = 0, notAns = 0, marked = 0;
  qs.forEach(q => {
    const st = STATE.status[q.id];
    if (st === 'answered')      ans++;
    else if (st === 'marked')   marked++;
    else if (st === 'not-answered') notAns++;
  });
  document.getElementById('statAnswered').textContent    = ans;
  document.getElementById('statNotAnswered').textContent = notAns;
  document.getElementById('statMarked').textContent      = marked;
}

// ══════════════════════════════════════════════
// NAVIGATION
// ══════════════════════════════════════════════

function goTo(delta) {
  const qs = STATE.questions[currentSection().id] || [];
  const newIdx = STATE.currentQIdx + delta;

  if (newIdx < 0) return;
  if (newIdx >= qs.length) {
    // Try to move to next section
    if (STATE.currentSectionIdx < STATE.sections.length - 1) {
      if (confirm(`Move to the next section: "${STATE.sections[STATE.currentSectionIdx+1].name}"? You cannot return to this section.`)) {
        STATE.currentSectionIdx++;
        STATE.currentQIdx = 0;
        clearInterval(STATE.activeTimer);
        startSectionTimer(currentSection().id);
        loadSection(currentSection().id);
        updateSectionProgressBar();
      }
    } else {
      showConfirmSubmit();
    }
    return;
  }

  STATE.currentQIdx = newIdx;
  renderQuestion();
}

function updateNavBtns() {
  const qs   = STATE.questions[currentSection().id] || [];
  const next = document.getElementById('btnNext');
  const prev = document.getElementById('btnPrev');
  prev.disabled = STATE.currentQIdx === 0;
  const isLast = STATE.currentQIdx === qs.length - 1;
  next.textContent = isLast ? 'Next Section →' : 'Next →';
}

function markForReview() {
  const qs = STATE.questions[currentSection().id] || [];
  const q  = qs[STATE.currentQIdx];
  if (!q) return;
  STATE.status[q.id] = 'marked';
  updatePaletteBtn(q.id);
  updateStats();
  goTo(1);
}

function clearResponse() {
  const qs = STATE.questions[currentSection().id] || [];
  const q  = qs[STATE.currentQIdx];
  if (!q) return;
  delete STATE.answers[q.id];
  STATE.status[q.id] = 'not-answered';
  // Clear UI
  document.querySelectorAll('.option-label').forEach(l => l.classList.remove('selected'));
  document.getElementById('fillInput').value = '';
  updatePaletteBtn(q.id);
  updateStats();
  saveAnswer(q.id, '');
}

// ══════════════════════════════════════════════
// SAVE ANSWER
// ══════════════════════════════════════════════

async function saveAnswer(qId, answer) {
  try {
    await fetch('/api/save_answer', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question_id: qId, answer })
    });
  } catch(e) { /* offline – handled by banner */ }
}

// Debounce for fill input
let _saveTimeout = null;
function saveAnswerDebounced(qId, answer) {
  clearTimeout(_saveTimeout);
  _saveTimeout = setTimeout(() => saveAnswer(qId, answer), 600);
}

// ══════════════════════════════════════════════
// SUBMIT
// ══════════════════════════════════════════════

function showConfirmSubmit() {
  // Build summary
  let html = '';
  STATE.sections.forEach(s => {
    const qs = STATE.questions[s.id] || [];
    let ans = 0;
    qs.forEach(q => { if (STATE.status[q.id] === 'answered') ans++; });
    html += `<div class="ss-row"><span>${s.name}</span><span>${ans}/${qs.length} answered</span></div>`;
  });
  document.getElementById('submitSummary').innerHTML = html;
  document.getElementById('confirmSubmitOverlay').classList.remove('hidden');
}

function closeConfirmSubmit() {
  document.getElementById('confirmSubmitOverlay').classList.add('hidden');
}

async function doFinalSubmit(autoTriggered = false) {
  closeConfirmSubmit();
  clearInterval(STATE.activeTimer);

  const payload = { answers: STATE.answers };

  try {
    const res  = await fetch('/api/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (data.redirect) {
      localStorage.clear();
      window.location = data.redirect;
    }
  } catch(e) {
    alert('Submission failed. Please check your connection.');
  }
}

// ══════════════════════════════════════════════
// SECTION PROGRESS BAR
// ══════════════════════════════════════════════

function updateSectionProgressBar() {
  STATE.sections.forEach((s, i) => {
    const el = document.getElementById('spb-' + s.id);
    if (!el) return;
    el.classList.remove('active', 'done');
    if (i < STATE.currentSectionIdx)      el.classList.add('done');
    else if (i === STATE.currentSectionIdx) el.classList.add('active');
  });
}

// ══════════════════════════════════════════════
// BOOTSTRAP
// ══════════════════════════════════════════════

async function init() {
  initSecurity();
  await initCamera();
  initTimers();
  updateSectionProgressBar();

  // Load first section
  const sec = currentSection();
  await loadSection(sec.id);
  startSectionTimer(sec.id);
}

// Start when DOM ready
document.addEventListener('DOMContentLoaded', init);

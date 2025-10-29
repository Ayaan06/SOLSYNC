const statusText = document.getElementById('statusText');
const logsEl = document.getElementById('logs');
const form = document.getElementById('botForm');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');

let logsTimer = null;
let localLogs = []; // client-side event lines
let lastServerLogs = [];
let controllerOfflineNoted = false;

function nowTs() {
  const d = new Date();
  return d.toLocaleTimeString([], { hour12: false });
}

function appendLocal(msg, level = 'UI') {
  localLogs.push(`[${nowTs()}] [${level}] ${msg}`);
  renderLogs();
}

function setStatus(text) {
  statusText.textContent = text;
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(text || `HTTP ${res.status}`);
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('application/json')) return res.json();
  return res.text();
}

function renderLogs() {
  const combined = [...lastServerLogs, ...localLogs];
  logsEl.textContent = combined.join('\n');
  logsEl.scrollTop = logsEl.scrollHeight;
}

async function refreshStatus() {
  try {
    const data = await api('/status');
    const running = !!data.running;
    setStatus(running ? `Running (pid ${data.pid})` : 'Idle');
    statusText.classList.remove('running','idle','offline');
    statusText.classList.add(running ? 'running' : 'idle');
    if (data.running && !logsTimer) startLogs();
    if (!data.running && logsTimer) stopLogs();
    controllerOfflineNoted = false;
  } catch (e) {
    setStatus('Controller offline');
    statusText.classList.remove('running','idle','offline');
    statusText.classList.add('offline');
    if (!controllerOfflineNoted) {
      appendLocal('Controller appears offline. Is the server running?', 'WARN');
      controllerOfflineNoted = true;
    }
  }
}

async function fetchLogs() {
  try {
    const data = await api('/logs?limit=800');
    lastServerLogs = data.logs || [];
    renderLogs();
  } catch (e) {
    // ignore transient errors
  }
}

function startLogs() {
  if (logsTimer) return;
  fetchLogs();
  logsTimer = setInterval(fetchLogs, 2000);
}

function stopLogs() {
  if (logsTimer) {
    clearInterval(logsTimer);
    logsTimer = null;
  }
}

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  startBtn.disabled = true;
  startBtn.classList.remove('pulse');
  appendLocal('Submitting start request...');
  setStatus('Starting...');

  const payload = {
    secretKeyBase58: document.getElementById('secretKeyBase58').value.trim(),
    trackWallet: document.getElementById('trackWallet').value.trim(),
    fixedBuy: parseFloat(document.getElementById('fixedBuy').value),
    sellPercent: parseFloat(document.getElementById('sellPercent').value),
    slippage: parseInt(document.getElementById('slippage').value, 10),
    priorityFee: parseFloat(document.getElementById('priorityFee').value),
    pool: document.getElementById('pool').value,
    denominatedInSol: document.getElementById('denominatedInSol').checked,
    rpcWsUrl: document.getElementById('rpcWsUrl').value.trim(),
    rpcHttpUrl: document.getElementById('rpcHttpUrl').value.trim(),
  };

  try {
    await api('/start', { method: 'POST', body: JSON.stringify(payload) });
    appendLocal('Start accepted by controller.', 'OK');
    setStatus('Running');
    startBtn.disabled = true;
    stopBtn.disabled = false;
    startLogs();
  } catch (err) {
    appendLocal(`Start failed: ${err.message}`, 'ERROR');
    alert(`Failed to start: ${err.message}`);
    startBtn.disabled = false;
    startBtn.classList.add('pulse');
  }
});

stopBtn.addEventListener('click', async () => {
  appendLocal('Sending stop request...');
  try {
    await api('/stop', { method: 'POST' });
    appendLocal('Bot stopped.', 'OK');
    setStatus('Stopped');
    statusText.classList.remove('running','offline');
    statusText.classList.add('idle');
    startBtn.disabled = false;
    stopBtn.disabled = true;
    stopLogs();
    startBtn.classList.add('pulse');
  } catch (err) {
    appendLocal(`Stop failed: ${err.message}`, 'ERROR');
    alert(`Failed to stop: ${err.message}`);
  }
});

refreshStatus();
setInterval(refreshStatus, 5000);

// Visual cue to start when idle
startBtn.classList.add('pulse');

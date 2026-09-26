const $ = (id) => document.getElementById(id);
let socket = null;
let ownStatus = { connected: false, msg: '' };

// Giá»¯ token/role trong sessionStorage Ä‘á»ƒ trang live.html má»Ÿ tá»« popup dÃ¹ng Ä‘Æ°á»£c (cÃ¹ng origin Pages)
function syncAuthStorage() {
  if (window.__TX_TOKEN) {
    try { sessionStorage.setItem('tx_token', window.__TX_TOKEN); } catch (_) {}
    try { localStorage.setItem('tx_token', window.__TX_TOKEN); } catch (_) {}
  }
  if (window.__TX_ROLE) {
    try { sessionStorage.setItem('tx_role', window.__TX_ROLE); } catch (_) {}
    try { localStorage.setItem('tx_role', window.__TX_ROLE); } catch (_) {}
  }
}
setInterval(syncAuthStorage, 2000);

// â”€â”€ Auto-discovery: launcher tá»± push link tunnel â†’ server-url.json â”€â”€â”€â”€â”€â”€
let discoUrl = "";
let discoLoaded = false;
async function loadDiscovery() {
  try {
    const r = await fetch("./server-url.json?v=" + Date.now(), { cache: "no-store" });
    const j = await r.json();
    if (j && typeof j.url === "string" && j.url.trim()) discoUrl = j.url.trim();
  } catch (_) {}
  discoLoaded = true;
  updateServerHost();
  // Náº¿u vá»«a tÃ¬m tháº¥y URL má»›i mÃ  chÆ°a ná»‘i Ä‘Æ°á»£c â†’ tá»± káº¿t ná»‘i láº¡i
  if (discoUrl && !(socket && socket.connected)) setTimeout(retryConnect, 400);
}
loadDiscovery();
setInterval(loadDiscovery, 30000);

// â”€â”€ Server URL: localStorage("tx_server") â†’ auto-discovery â†’ config.js â†’ same-origin â”€â”€
function serverUrl() {
  let v = "";
  try { v = localStorage.getItem("tx_server") || ""; } catch (_) {}
  if (v) return v.trim();
  if (discoUrl) return discoUrl;
  return (window.__TX_SERVER || "").trim();
}
function getServerOverride() {
  try { return (localStorage.getItem("tx_server") || "").trim(); } catch (_) { return ""; }
}

// Hiá»ƒn thá»‹ lá»—i káº¿t ná»‘i trÃªn statusLine (tool.html)
function setSockStatus(msg) {
  const el = $('statusLine');
  if (el) { el.textContent = msg; el.className = 'status err'; }
}

// Tráº¡ng thÃ¡i phiÃªn Chrome CDP RIÃŠNG cá»§a user (server gá»­i qua user-status)
function updateOwnUi() {
  const el = $('ownLine');
  if (el) {
    if (ownStatus && ownStatus.agent) {
      el.textContent = 'âœ“ Chrome má»Ÿ táº¡i mÃ¡y báº¡n â€” chÆ¡i trá»±c tiáº¿p, dá»± Ä‘oÃ¡n theo bÃ n riÃªng';
      el.className = 'own-line on';
    } else {
      el.textContent = ownStatus.connected ? 'âœ“ Chrome CDP cá»§a báº¡n Ä‘Ã£ sáºµn sÃ ng' : (ownStatus.msg || 'ChÆ°a cÃ³ phiÃªn â€” nháº¥n Káº¾T Ná»I TOOL');
      el.className = 'own-line' + (ownStatus.connected ? ' on' : '');
    }
  }
}

// Panel dá»± Ä‘oÃ¡n bÃ n-riÃªng khi Chrome cháº¡y táº¡i mÃ¡y user (agent)
function renderAgentPanel(p) {
  if (!p) return;
  const pk = $('predPick'), pt = $('pctT'), px = $('pctX'), pc = $('predConf'), adv = $('predAdvice');
  if (!pk || !pt) return;
  if (p.pick) {
    pk.textContent = String(p.pick).toUpperCase() === 'T' ? 'TÃ€I' : 'Xá»ˆU';
    pk.className = 'side ' + (String(p.pick).toUpperCase() === 'T' ? 't' : 'x');
    pt.textContent = (p.pT != null ? Math.round(p.pT) : 50) + '%';
    px.textContent = (p.pX != null ? Math.round(p.pX) : 50) + '%';
    pc.innerHTML = 'Ä‘á»™ tin cáº­y <b>' + (p.conf != null ? Math.round(p.conf) : 50) + '%</b>';
    const bT = $('barT'), bX = $('barX');
    if (bT) bT.style.width = (p.pT != null ? p.pT : 50) + '%';
    if (bX) bX.style.width = (p.pX != null ? p.pX : 50) + '%';
    adv.textContent = p.skip ? ('Tin cáº­y tháº¥p (' + Math.round(p.conf) + '%) â†’ NÃŠN Bá»Ž VÃN (bÃ n riÃªng cá»§a báº¡n)') : (String(p.pick).toUpperCase() === 'T' ? 'TÃ€I' : 'Xá»ˆU') + ' má»©c Kelly ' + (p.kelly != null ? p.kelly : '--') + '% â€” bÃ n riÃªng cá»§a báº¡n';
    adv.className = 'pred-advice ' + (p.skip ? 'warn' : 'go');
    const badge = $('phaseBadge');
    if (badge) badge.textContent = 'BÃ€N RIÃŠNG';
  }
  if (Array.isArray(p.hist) && typeof renderChips === 'function') renderChips(p.hist.slice(-30));
  const lastEl = $('predLast');
  if (lastEl && p.lastResult) {
    lastEl.style.display = '';
    lastEl.innerHTML = 'Káº¿t quáº£: <span class="result ' + String(p.lastResult).toLowerCase() + '">' + (String(p.lastResult).toUpperCase() === 'T' ? 'TÃ€I' : 'Xá»ˆU') + '</span>';
  }
}

// Má»Ÿ mÃ n hÃ¬nh 1:1 cá»§a chÃ­nh mÃ¬nh trong tab/popup riÃªng
function openLivePopup() {
  if (window.__TX_TOKEN) {
    try { localStorage.setItem('tx_token', window.__TX_TOKEN); } catch (_) {}
    try { sessionStorage.setItem('tx_token', window.__TX_TOKEN); } catch (_) {}
  }
  if (window.__TX_ROLE) {
    try { localStorage.setItem('tx_role', window.__TX_ROLE); } catch (_) {}
  }
  const pop = window.open('live.html?v=20260919c', 'txlive' + Date.now(), 'width=1310,height=780,resizable=yes,scrollbars=no,status=no');
  if (pop) pop.focus();
}

// Cáº­p nháº­t Ã´ "Server" trÃªn thanh feed-note
function updateServerHost() {
  const sh = $('serverHost');
  if (!sh) return;
  const u = serverUrl();
  sh.textContent = (socket && socket.connected ? '' : 'âš  ') + (u || location.host);
}

// Táº£i socket.io-client tá»« server Ä‘Ã£ cáº¥u hÃ¬nh (GitHub Pages khÃ´ng cÃ³ /socket.io)
let ioLoad = null;
function ensureSocketIO() {
  if (window.io) return Promise.resolve();
  if (ioLoad) return ioLoad;
  ioLoad = new Promise((resolve, reject) => {
    const url = serverUrl() || location.origin;
    const s = document.createElement("script");
    s.src = url + "/socket.io/socket.io.js";
    s.onload = () => resolve();
    s.onerror = () => { ioLoad = null; reject(new Error("KhÃ´ng táº£i Ä‘Æ°á»£c socket.io tá»« " + url)); };
    document.head.appendChild(s);
  });
  return ioLoad;
}

let lastToken = null;
let lastAttemptUrl = "";
let socketBusy = false;
let socketSuperseded = false;
async function initSocket(authToken) {
  if (socket) return socket;
  if (socketSuperseded) return socket;
  if (socketBusy) return socket;
  socketBusy = true;
  lastToken = authToken || lastToken;
  // Äá»£i discovery server-url.json tá»‘i Ä‘a 1.5s (thÆ°á»ng load xong trÆ°á»›c auth)
  if (!discoLoaded) await new Promise(r => setTimeout(r, 1500));
  try {
    await ensureSocketIO();
  } catch (e) {
    log('Lá»—i náº¡p socket.io: ' + e.message, 'err');
    setSockStatus('Lá»—i káº¿t ná»‘i â€” khÃ´ng Ä‘á»c Ä‘Æ°á»£c socket.io tá»« "' + (serverUrl() || location.origin) + '". Báº¥m "Ä‘á»•i" á»Ÿ feed-note hoáº·c kiá»ƒm tra server.');
    socketBusy = false;
    return null;
  }
  const url = serverUrl();
  lastAttemptUrl = url || "";
  socket = io(url || undefined, { auth: { token: lastToken }, transports: ['websocket', 'polling'] });
  window.socket = socket;
  bindSocketEvents();
  socketBusy = false;
  return socket;
}

// Tá»± ná»‘i láº¡i khi URL server Ä‘á»•i (vd: launcher vá»«a push link tunnel má»›i)
function retryConnect() {
  if (!lastToken) return;
  if (socketSuperseded) return;   // tab nay da bi ket noi moi day ra, dung tranh doi phiên
  const want = serverUrl() || "";
  const urlChanged = want !== lastAttemptUrl;
  const dead = !(socket && socket.connected);
  if (!urlChanged && !dead) return;
  if (socket) { try { socket.disconnect(); } catch (_) {} socket = null; }
  initSocket(lastToken);
}

function getSocket() { return socket; }
window.initSocket = initSocket;
window.getSocket = getSocket;

const STRAT_NAMES = {
  trendFollow: 'Äuá»•i xu hÆ°á»›ng',
  reversal: 'Äáº£o chiá»u',
  patternMatch: 'Soi cáº§u',
  overloadReversal: 'BÃ£o hÃ²a',
  meanRevert: 'CÃ¢n báº±ng',
  empiricalBias: 'Bias',
};

const state = { snapshot: null, lastNoteTs: 0 };
let launchOnReady = false;

function log(msg, kind) {
  const box = $('log');
  const d = document.createElement('div');
  if (kind) d.className = kind;
  d.textContent = '[' + new Date().toLocaleTimeString() + '] ' + msg;
  box.appendChild(d);
  while (box.childElementCount > 400) box.removeChild(box.firstChild);
  box.scrollTop = box.scrollHeight;
}

function render(snap) {
  state.snapshot = snap;
  const { status, capturing, prediction, stats, history, lastResult, lastWin, config } = snap;
  const mode = (config && config.mode) || 'feed';

  // Note log with throttle for frame spam
  if (snap.note && snap.note !== state.lastNote) {
    const now = Date.now();
    const isFrame = /^WS-(FRAME\[|SENT )/.test(snap.note);
    if (isFrame && now - state.lastNoteTs < 300) { state.lastNote = snap.note; return; }
    if (!isFrame) state.lastNoteTs = now;
    state.lastNote = snap.note;
    log(snap.note);
  }

  // Connection badge
  const badge = $('connBadge');
  const sockLive = !!(getSocket() && getSocket().connected);
  const hasData = !!(prediction || (history && history.length > 0));
  const feeding = mode === 'feed' && sockLive;
  const active = status.connected || (feeding && hasData);
  if (status.connected) { badge.className = 'badge on'; badge.textContent = 'ONLINE'; }
  else if (feeding && hasData) { badge.className = 'badge on'; badge.textContent = 'ONLINE'; }
  else if (feeding) { badge.className = 'badge mid'; badge.textContent = 'Sáº´N SÃ€NG'; }
  else if (status.msg && status.msg.includes('Äang')) { badge.className = 'badge mid'; badge.textContent = 'CONNECTING'; }
  else { badge.className = 'badge off'; badge.textContent = 'OFFLINE'; }

  $('statusLine').textContent = status.msg || '';
  $('statusLine').className = 'status' + (status.msg && (status.msg.startsWith('Lá»—i') || status.msg.includes('tháº¥t báº¡i')) ? ' err' : '');
  if (mode === 'feed' && sockLive && !status.connected && !status.msg) {
    $('statusLine').textContent = hasData ? 'Äang nháº­n káº¿t quáº£ â€” ' + (history ? history.length : 0) + ' vÃ¡n' : 'Server sáºµn sÃ ng â€” nháº¥n Káº¾T Ná»I TOOL Ä‘á»ƒ má»Ÿ phiÃªn';
    $('statusLine').className = 'status';
  }
  $('btnDisconnect').disabled = !status.connected;

  // Grid luÃ´n hiá»ƒn thá»‹; khi offline hiá»‡n placeholder thay vÃ¬ áº©n háº¿t
  $('mainGrid').style.display = '';
  const ui = $('urlInput'); if (ui) ui.value = (config && config.url) || '';
  const pi = $('portInput'); if (pi) pi.value = config ? config.cdpPort : 9222;

  const sh = $('shareUrl');
  if (sh) sh.textContent = location.href;
  const ob = $('btnOpenGame');
  if (ob && config && config.url && !ob.dataset.wired) {
    ob.dataset.wired = '1';
    ob.onclick = () => { bindGameMsg(); const w = window.open(config.url, 'txgame'); if (w) gameWin = w; };
  }
  const srv = $('serverHost');
  if (srv) srv.textContent = (sockLive ? '' : 'âš  ') + (serverUrl() || location.host);
  const sv = $('setServer');
  if (sv) {
    sv.onclick = (e) => {
      e.preventDefault();
      const v = prompt('Äá»‹a chá»‰ server dá»± Ä‘oÃ¡n (Ä‘á»ƒ trá»‘ng = dÃ¹ng máº·c Ä‘á»‹nh):', serverUrl());
      if (v === null) return;
      try { localStorage.setItem('tx_server', v.trim()); } catch (_) {}
      location.reload();
    };
  }
  const cp = $('copySnip');
  if (cp && !cp.dataset.wired) {
    cp.dataset.wired = '1';
    cp.onclick = async (e) => {
      e.preventDefault();
      const src = (serverUrl() || location.origin) + '/api/snip.js';
      const bm = 'javascript:(function(){var s=document.createElement("script");s.src="' + src + '";document.head.appendChild(s);})();';
      try {
        if (navigator.clipboard && navigator.clipboard.writeText) { await navigator.clipboard.writeText(bm); }
        else { const ta = document.createElement('textarea'); ta.value = bm; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
        const fs = $('feedSrc'); if (fs) fs.textContent = 'ÄÃ£ chÃ©p plugin soi â€” dÃ¡n vÃ o Console tab web game';
      } catch (_) { alert('Copy tháº¥t báº¡i â€” plugin: ' + bm); }
    };
  }

  if (!active) {
    const pb = $('predBox');
    pb.className = 'pred-box';
    const pbBadge = $('phaseBadge'); if (pbBadge) { pbBadge.textContent = 'CHá»œ Dá»® LIá»†U'; pbBadge.className = 'phase-badge idle'; }
    const pbLine = $('phaseLine'); if (pbLine) { pbLine.textContent = 'chá» káº¿t ná»‘i'; pbLine.className = 'phase-line g'; }
    $('predPick').textContent = '--';
    $('predPick').className = 'side';
    $('pctT').textContent = '50%';
    $('pctX').textContent = '50%';
    $('predConf').textContent = 'chá» káº¿t ná»‘i';
    $('predAdvice').textContent = 'Nháº¥n Káº¾T Ná»I TOOL â€” server má»Ÿ/giá»¯ phiÃªn Chrome CDP soi bÃ n chung, má»i thiáº¿t bá»‹ cÃ¹ng xem dá»± Ä‘oÃ¡n';
    $('predAdvice').className = 'pred-advice off';
    $('predVotes').innerHTML = '';
    $('predLast').style.display = 'none';
    renderChips([]);
    $('statsList').innerHTML = '';
    $('accBig').textContent = '--';
    $('accBig').className = 'acc-big';
    $('accSub').textContent = '0 dá»± Ä‘oÃ¡n';
    $('consensus').innerHTML = '';
    $('bestThresh').innerHTML = '';
    $('stratTable').innerHTML = '';
    $('biasNote').textContent = '';
    $('liveView').src = '';
    $('liveView').removeAttribute('data-ready');
    $('liveView').style.display = '';
    renderChart([], []);
    if ($('liveMask')) $('liveMask').style.display = '';
    if ($('liveMask')) $('liveMask').innerHTML = 'CHÆ¯A CÃ“ HÃŒNH<br>' + (sockLive ? 'Äang chá» khung hÃ¬nh tá»« mÃ¡y chá»§' : 'ChÆ°a káº¿t ná»‘i server');
    return;
  }

  // Live view cá»§a báº¡n (Chrome CDP riÃªng theo user)
  const lc = $('liveCard');
  if (lc) lc.style.display = window.__TX_ROLE ? '' : 'none';
  updateOwnUi();

  // Live view diagnostics badge
  const sc = snap.screen || {};
  const liveB = $('liveBadge');
  if (liveB) {
    if (config && config.stream) {
      const age = sc.lastAt ? Math.round((Date.now() - sc.lastAt) / 100) / 10 + 's' : '--';
      if (sc.running) liveB.textContent = 'áº¢nh: ' + sc.frames + ' frame Â· má»›i ' + age;
      else liveB.textContent = 'áº¢nh: dá»«ng' + (sc.lastErr ? ' (' + sc.lastErr + ')' : '');
      liveB.style.color = sc.running && sc.lastAt && Date.now() - sc.lastAt < 3000 ? '#22c55e' : (sc.running ? '#facc15' : '#ef4444');
    } else {
      liveB.textContent = 'áº¢nh: Táº®T';
      liveB.style.color = '#94a3b8';
    }
  }

  // ========== PREDICTION BOX ==========
  const pb = $('predBox');
  const hasResult = !!lastResult;
  const hasPrediction = !!prediction;

  // Phase badge/status (synced with the in-game overlay)
  const ph = snap.phase || 'IDLE';
  const phMap = { WAIT: ['wait', 'CHá»œ PHIÃŠN Má»šI'], ANALYZE: ['analyze', 'ÄANG PHÃ‚N TÃCH'], READY: ['ready', hasPrediction && prediction.skip ? 'CÃ‚N NHáº®C' : 'CÆ¯á»¢C!'], GET_RESULT: ['get', 'ÄANG Láº¤Y Káº¾T QUáº¢'], REVEAL: ['reveal', 'Káº¾T QUáº¢'], IDLE: ['idle', 'CHá»œ Dá»® LIá»†U'] };
  const [phCls, phTxt] = phMap[ph] || phMap.IDLE;
  const pbBadge = $('phaseBadge'), pbLine = $('phaseLine');
  pbBadge.className = 'phase-badge ' + phCls + (ph === 'READY' && hasPrediction && prediction.skip ? ' skips' : '');
  pbBadge.textContent = phTxt;
  pbLine.className = 'phase-line' + (ph === 'WAIT' || ph === 'GET_RESULT' ? ' y' : ph === 'IDLE' ? ' g' : '');
  pbLine.innerHTML = (ph === 'WAIT' || ph === 'ANALYZE' || ph === 'GET_RESULT') ? phTxt + '<span class="dot">...</span>' : (ph === 'REVEAL' && lastResult ? 'Káº¾T QUáº¢: ' + (lastResult === 'T' ? 'TÃ€I' : 'Xá»ˆU') : (ph === 'IDLE' ? 'Chá» round má»›i...' : ''));

  // Reset border classes
  pb.className = 'pred-box' + (hasPrediction ? ' ready' : '');
  if (hasResult && lastWin !== null) {
    pb.className += lastWin ? ' win' : ' lose';
  }

  if (hasPrediction) {
    $('pctT').textContent = prediction.pT + '%';
    $('pctX').textContent = prediction.pX + '%';
    const pk = $('predPick');
    pk.textContent = prediction.pick === 'T' ? 'TÃ€I' : 'Xá»ˆU';
    pk.className = 'side ' + prediction.pick.toLowerCase();
    $('predConf').innerHTML = 'Ä‘á»™ tin cáº­y <b>' + prediction.confidence + '%</b>';
    $('barT').style.width = prediction.pT + '%';
    $('barX').style.width = prediction.pX + '%';
  } else {
    $('pctT').textContent = '50%';
    $('pctX').textContent = '50%';
    $('predPick').textContent = '--';
    $('predPick').className = 'side';
    $('predConf').innerHTML = history && history.length >= 3 ? 'Ä‘á»£i dá»¯ liá»‡u...' : 'cáº§n â‰¥3 vÃ¡n';
    $('barT').style.width = '50%';
    $('barX').style.width = '50%';
  }

  // Advice line
  const adv = $('predAdvice');
  if (!prediction) { adv.textContent = ''; adv.className = 'pred-advice'; }
  else if (prediction.skip) { adv.textContent = 'Tin cáº­y tháº¥p (' + prediction.confidence + '%) â†’ NÃŠN Bá»Ž VÃN'; adv.className = 'pred-advice warn'; }
  else if (prediction.kellyB <= 0) { adv.textContent = 'Lá»£i tháº¿ tháº¥p â†’ nÃªn bá» hoáº·c cÆ°á»£c tá»‘i thiá»ƒu'; adv.className = 'pred-advice warn'; }
  else { adv.textContent = 'Kelly ' + prediction.kellyB + '% â€” cÆ°á»£c ' + (prediction.pick === 'T' ? 'TÃ€I' : 'Xá»ˆU'); adv.className = 'pred-advice go'; }

  // Strategy votes (compact pills)
  const votes = prediction && prediction.votes ? prediction.votes : [];
  const vBox = $('predVotes');
  vBox.innerHTML = '';
  for (const v of votes) {
    const strat = stats && stats.strategyRates[v.name];
    const rate = strat ? strat.recentRate : '--';
    const p = document.createElement('span');
    p.className = 'pill';
    p.innerHTML = '<b>' + (STRAT_NAMES[v.name] || v.name) + '</b> â†’ <span class="' + (v.pick === 'T' ? 'vt' : 'vx') + '">' + v.pick + '</span> ' + rate + '%';
    vBox.appendChild(p);
  }

  // Last result indicator
  const lastEl = $('predLast');
  if (hasResult && lastWin !== null) {
    lastEl.style.display = '';
    lastEl.innerHTML =
      'Káº¿t quáº£: <span class="result ' + lastResult.toLowerCase() + '">' + (lastResult === 'T' ? 'TÃ€I' : 'Xá»ˆU') + '</span>' +
      (lastWin ? '<span class="outcome win">âœ“ ÄÃšNG</span>' : '<span class="outcome lose">âœ— SAI</span>');
  } else {
    lastEl.style.display = 'none';
  }

  // History chips
  renderChips(history ? history.slice(-30) : []);
  renderChart(snap.recentSums || [], history || []);

  // ========== STATS ==========
  if (stats) {
    // Summary stats
    const streak = stats.currentStreak ? (stats.currentStreak.side === 'T' ? 'TÃ€I' : 'Xá»ˆU') + ' Ã—' + stats.currentStreak.len : '--';
    const sums = snap.recentSums || [];
    const avgSum = sums.length ? Math.round((sums.reduce((a, b) => a + b, 0) / sums.length) * 10) / 10 : '--';
    $('statsList').innerHTML = [
      ['Tá»•ng', stats.total],
      ['TÃ€I', stats.t, 't'],
      ['Xá»ˆU', stats.x, 'x'],
      ['Tá»· lá»‡ T', stats.tRate + '%'],
      ['TB tá»•ng (12 vÃ¡n)', avgSum],
      ['Chuá»—i hiá»‡n táº¡i', streak],
      ['Chuá»—i dÃ i nháº¥t', stats.longestStreak],
    ].map(([k, v, cls]) => '<div class="row"><span class="k">' + k + '</span><span class="v ' + (cls || '') + '">' + v + '</span></div>').join('');

    // Accuracy
    const accEl = $('accBig');
    if (stats.accuracy > 0) {
      accEl.textContent = stats.accuracy + '%';
      accEl.className = 'acc-big' + (stats.accuracy >= 55 ? ' go' : stats.accuracy >= 48 ? ' warn' : ' bad');
    } else {
      accEl.textContent = '--';
      accEl.className = 'acc-big';
    }
    $('accSub').textContent = stats.predictionCount + ' dá»± Ä‘oÃ¡n Â· ' + (stats.strategyRates.trendFollow ? stats.strategyRates.trendFollow.total : 0) + ' máº«u luyá»‡n';

    // Consensus bar (how many strategies agree with main pick)
    const votesArr = prediction && prediction.votes ? prediction.votes : [];
    if (votesArr.length > 0 && prediction) {
      const agree = votesArr.filter(v => v.pick === prediction.pick).length;
      const total = votesArr.length;
      $('consensus').innerHTML = Array.from({length: 5}, (_, i) =>
        '<div class="bar' + (i < agree ? ' on' : '') + '"></div>'
      ).join('') + '<span style="font-size:10px;color:var(--dim);margin-left:4px">' + agree + '/' + total + ' Ä‘á»“ng thuáº­n</span>';
    } else {
      $('consensus').innerHTML = '';
    }

    // Best threshold
    const bt = stats.bestThreshold;
    $('bestThresh').innerHTML = bt && bt.total > 0
      ? '<div style="font-size:11px;color:var(--dim)">NgÆ°á»¡ng tá»‘i Æ°u: <b style="color:var(--text)">' + bt.t + '% tin cáº­y</b> â†’ hit ' + bt.rate + '% (' + bt.total + ' vÃ¡n)</div>'
      : '';

    // Strategy table (compact)
    const names = ['trendFollow', 'reversal', 'patternMatch', 'overloadReversal', 'meanRevert', 'empiricalBias'];
    $('stratTable').innerHTML = names.map(key => {
      const s = stats.strategyRates[key];
      if (!s || s.total === 0) return '';
      const cls = s.recentRate >= 55 ? 'go' : s.recentRate >= 45 ? '' : 'bad';
      return '<div class="strat-row"><span class="name">' + (STRAT_NAMES[key] || key) + '</span><span style="color:var(--dim);font-size:11px">' + s.wins + '/' + s.total + '</span><span class="rate ' + cls + '">' + s.recentRate + '%</span></div>';
    }).filter(Boolean).join('');

    // Bias note
    const b = stats.bias;
    const bn = $('biasNote');
    if (b && b.detected) {
      bn.textContent = 'âš  BIAS: ' + b.recentN + ' vÃ¡n gáº§n nghiÃªng vá» ' + (b.side === 'T' ? 'TÃ€I' : 'Xá»ˆU') + ' (z=' + b.z + ')';
      bn.style.color = 'var(--warn)';
    } else {
      bn.textContent = '';
    }
  }
}

function renderChips(arr) {
  const box = $('historyChips');
  box.innerHTML = '';
  arr.forEach((c, i) => {
    const d = document.createElement('div');
    d.className = 'chip ' + c.toLowerCase() + (i === arr.length - 1 ? ' last' : '');
    d.textContent = c;
    box.appendChild(d);
  });
}

function renderChart(sums, hist) {
  const svg = $('chartSvg');
  const trendEl = $('trendTag');
  if (!svg || !trendEl) return;
  const n = sums ? sums.length : 0;
  if (!n || n < 2) {
    svg.innerHTML = '<text x="140" y="85" fill="#64748b" font-size="11" text-anchor="middle">ChÆ°a Ä‘á»§ dá»¯ liá»‡u</text>';
    trendEl.className = 'trend-tag';
    trendEl.innerHTML = '<span class="ms">trending_flat</span> --';
    return;
  }
  const W = 280, H = 160, padT = 14, padB = 20, padL = 2, padR = 2;
  const innerW = W - padL - padR;
  const innerH = H - padT - padB;
  let mn = Math.min.apply(null, sums), mx = Math.max.apply(null, sums);
  if (mn === mx) { mx = mn + 3; }
  const range = mx - mn;
  const padRange = range * 0.15;
  mn = Math.max(1, mn - padRange);
  mx = mx + padRange;
  const yScale = (v) => padT + innerH - ((v - mn) / (mx - mn)) * innerH;
  const xStep = innerW / (n - 1);
  const W105 = 10.5;

  let svgStr = '';

  // Grid horizontal lines
  for (let g = 0; g < 5; g++) {
    const gy = padT + (innerH / 4) * g;
    svgStr += '<line x1="0" y1="' + gy + '" x2="' + W + '" y2="' + gy + '" stroke="#1e293b" stroke-width="0.7"/>';
  }

  // Boundary line 10.5
  const y105 = yScale(W105);
  if (y105 >= padT && y105 <= H - padB) {
    svgStr += '<line x1="0" y1="' + y105 + '" x2="' + W + '" y2="' + y105 + '" stroke="#facc15" stroke-width="0.7" stroke-dasharray="3,3" opacity="0.45"/>';
    svgStr += '<text x="' + (W - 2) + '" y="' + (y105 - 2) + '" fill="#facc15" font-size="7" opacity="0.5" text-anchor="end">10.5</text>';
  }

  // Area fill
  const baseY = yScale(W105);
  let areaT = '', areaX = '';
  const pts = [];
  for (let i = 0; i < n; i++) {
    const x = padL + i * xStep;
    const y = yScale(sums[i]);
    pts.push(x + ',' + y);
  }
  const areaPath = 'M' + padL + ',' + baseY + ' L' + pts.join(' L') + ' L' + (padL + (n - 1) * xStep) + ',' + baseY + ' Z';

  // Split into T (above) and X (below) areas for gradient effect
  svgStr += '<defs><linearGradient id="areaG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ef4444" stop-opacity="0.25"/><stop offset="100%" stop-color="#3b82f6" stop-opacity="0.25"/></linearGradient></defs>';
  svgStr += '<path d="' + areaPath + '" fill="url(#areaG)"/>';

  // Line + candles
  for (let i = 0; i < n; i++) {
    const x = padL + i * xStep;
    const y = yScale(sums[i]);
    const isT = sums[i] > W105;
    const col = isT ? '#ef4444' : '#3b82f6';
    const bw = Math.max(4, Math.min(8, xStep * 0.45));
    const halfBw = bw / 2;

    // Candle body
    const bodyTop = isT ? y : yScale(W105);
    const bodyBot = isT ? yScale(W105) : y;
    const bodyH = Math.max(2, bodyBot - bodyTop);
    svgStr += '<rect x="' + (x - halfBw) + '" y="' + bodyTop + '" width="' + bw + '" height="' + bodyH + '" rx="1" fill="' + col + '" opacity="0.85"/>';

    // Wick
    svgStr += '<line x1="' + x + '" y1="' + (y - 2) + '" x2="' + x + '" y2="' + (y + 2) + '" stroke="' + col + '" stroke-width="1.2" opacity="0.5"/>';
  }

  // MA5 line
  const maPts = [];
  for (let i = 0; i < n; i++) {
    if (i < 4) continue;
    let sum = 0;
    for (let j = i - 4; j <= i; j++) sum += sums[j];
    const avg = sum / 5;
    const x = padL + i * xStep;
    const y = yScale(avg);
    maPts.push(x + ',' + y);
  }
  if (maPts.length > 1) {
    svgStr += '<polyline points="' + maPts.join(' ') + '" fill="none" stroke="#f5c842" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" opacity="0.8"/>';
  }

  // Last point glow
  const lastX = padL + (n - 1) * xStep;
  const lastY = yScale(sums[n - 1]);
  const lastCol = sums[n - 1] > W105 ? '#ef4444' : '#3b82f6';
  svgStr += '<circle cx="' + lastX + '" cy="' + lastY + '" r="4" fill="' + lastCol + '" opacity="0.35"/>';
  svgStr += '<circle cx="' + lastX + '" cy="' + lastY + '" r="2.5" fill="' + lastCol + '"/>';

  svg.innerHTML = svgStr;

  // Trend tag
  const lastSum = sums[n - 1];
  const prevSum = sums[Math.max(0, n - 6)] || lastSum;
  let trendCls, trendText;
  if (lastSum > prevSum + 1.5) { trendCls = 'up'; trendText = 'â–² TÃ€I â‡§'; }
  else if (lastSum < prevSum - 1.5) { trendCls = 'down'; trendText = 'â–¼ Xá»ˆU â‡©'; }
  else { trendCls = 'flat'; trendText = 'â†’ Äi ngang'; }
  trendEl.className = 'trend-tag ' + trendCls;
  trendEl.innerHTML = '<span class="ms">' + (trendCls === 'up' ? 'trending_up' : trendCls === 'down' ? 'trending_down' : 'trending_flat') + '</span> ' + trendText;
}

// ===== Socket events =====
function bindSocketEvents() {
  socket.on('snapshot', render);
  socket.on('connect', () => {
    const u = serverUrl();
    log('ÄÃ£ káº¿t ná»‘i server: ' + (u || 'cÃ¹ng nguá»“n'));
    updateServerHost();
    setSockStatus('ÄÃ£ káº¿t ná»‘i â€” ' + (u || location.host));
    if (window.__TX_ROLE && launchOnReady) { launchOnReady = false; socket.emit('launch-profile', {}); }
  });
  socket.on('disconnect', (reason) => {
    log('Máº¥t káº¿t ná»‘i: ' + reason, 'err');
    updateServerHost();
    setSockStatus('Máº¥t káº¿t ná»‘i server â€” ' + reason);
    loadDiscovery(); // tunnel cÃ³ thá»ƒ vá»«a restart â†’ láº¥y URL má»›i ngay
  });
  socket.on('connect_error', (err) => {
    const u = serverUrl() || location.origin;
    log('Lá»—i káº¿t ná»‘i: ' + (err.message || err), 'err');
    updateServerHost();
    // Override tay Ä‘ang trá» URL cháº¿t mÃ  auto-discovery cÃ³ URL khÃ¡c â†’ tá»± quÃªn override vÃ  thá»­ láº¡i
    const ov = getServerOverride();
    if (ov && discoUrl && ov !== discoUrl) {
      setSockStatus('Lá»—i káº¿t ná»‘i "' + u + '" â€” Ä‘ang chuyá»ƒn vá» server tá»± Ä‘á»™ng "' + discoUrl + '"...');
      try { localStorage.removeItem('tx_server'); } catch (_) {}
      if (socket) { try { socket.disconnect(); } catch (_) {} socket = null; }
      initSocket(lastToken);
      return;
    }
    setSockStatus('Lá»—i káº¿t ná»‘i "' + u + '" â€” ' + (err.message || 'kiá»ƒm tra server Ä‘Ã£ báº­t chÆ°a') + '. Äang tá»± tÃ¬m server...');
    loadDiscovery(); // láº¥y ngay URL tunnel má»›i nháº¥t náº¿u server-url.json vá»«a Ä‘á»•i
  });
  socket.on('user-status', (d) => {
    ownStatus = (d && typeof d === 'object') ? d : { connected: false, msg: '' };
    updateOwnUi();
  });
  socket.on('panel-push', (pay) => {
    // Không chặn theo ownStatus.agent: agent rớt tạm thời sẽ làm panel đứng hình,
    // và lúc reconnect payload rỗng sẽ xoá sạch dải lịch sử. user-status chỉ lo statusLine.
    if (pay) renderAgentPanel(pay);
  });
  socket.on('session-replaced', () => {
    // Server đã đóng socket cũ vì có phiên mới đăng nhập. Ngắt im và không giành lại,
    // nếu không hai tab cùng tài khoản sẽ đẩy qua đẩy lại vô hạn.
    socketSuperseded = true;
    try { socket.disconnect(); } catch (_) {}
    setSockStatus('Phiên này đã được kết nối mới thay thế. Nếu bạn vẫn muốn dùng, hãy tải lại trang.');
  });
  socket.on('screen', (buf) => {
    const now = Date.now();
    if (now - lastScreenT < 50) return;
    lastScreenT = now;
    const img = $('liveView');
    const mask = $('liveMask');
    if (!img) return;
    try { if (img.__url) URL.revokeObjectURL(img.__url); } catch (_) {}
    img.__url = URL.createObjectURL(new Blob([buf], { type: 'image/jpeg' }));
    img.src = img.__url;
    img.dataset.ready = '1';
    if (mask) mask.style.display = 'none';
  });
}

$('btnConnect').onclick = () => {
  const s = getSocket();
  const role = window.__TX_ROLE;
  if (s && s.connected) {
    if (role) {
      log('Äang má»Ÿ Chrome CDP riÃªng cá»§a báº¡n...');
      setSockStatus('Äang má»Ÿ Chrome CDP cá»§a báº¡n...');
      s.emit('launch-profile', {});
    } else {
      log('ChÆ°a Ä‘Äƒng nháº­p â€” Ä‘Äƒng nháº­p Ä‘á»ƒ táº¡o phiÃªn Chrome CDP riÃªng.', 'err');
      setSockStatus('ÄÄƒng nháº­p trÆ°á»›c khi dÃ¹ng Káº¾T Ná»I.');
    }
    return;
  }
  if (!s && window.__TX_TOKEN && typeof initSocket === 'function') {
    launchOnReady = !!role;
    log(launchOnReady ? 'Äang káº¿t ná»‘i server â€” sáº½ tá»± má»Ÿ phiÃªn Chrome CDP cá»§a báº¡n...' : 'Äang káº¿t ná»‘i server...');
    setSockStatus('Äang káº¿t ná»‘i server...');
    initSocket(window.__TX_TOKEN);
  }
};
const bol = $('btnOpenLive');
if (bol) bol.onclick = () => openLivePopup();

// Ná»‘i Chrome cháº¡y táº¡i MÃY Báº N (agent outbound) â€” mÆ°á»£t tuyá»‡t Ä‘á»‘i, khÃ´ng stream server
const bAg = $('btnAgent');
if (bAg) bAg.onclick = () => {
  const s = getSocket();
  if (!s || !s.connected) {
    setSockStatus('Káº¿t ná»‘i server trÆ°á»›c (báº¥m Káº¾T Ná»I TOOL) rá»“i báº¥m CHROME MÃY Báº N.');
    return;
  }
  s.emit('agent-pair', {}, (r) => {
    const code = r && r.code;
    if (!code) { setSockStatus('ChÆ°a láº¥y Ä‘Æ°á»£c mÃ£ liÃªn káº¿t. Thá»­ láº¡i.'); return; }
    const ov = $('agentOv');
    if (!ov) { alert('MÃ£ liÃªn káº¿t: ' + code); return; }
    const cd = $('agentCode'); if (cd) cd.textContent = code;
    const base = (serverUrl() || location.origin).replace(/\/+$/, '');
    const cmd = 'curl.exe -L -o agent_chrome.bat "' + base + '/agent_chrome.bat"\r\nagent_chrome.bat ' + code + ' "' + base + '"';
    const ce = $('agentCmd'); if (ce) ce.textContent = cmd;
    ov.style.display = 'flex';
  });
};
const bAc = $('agentClose');
if (bAc) bAc.onclick = () => { const o = $('agentOv'); if (o) o.style.display = 'none'; };
const bAcopy = $('agentCopy');
if (bAcopy) bAcopy.onclick = () => {
  const t = $('agentCmd'); if (!t) return;
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) { navigator.clipboard.writeText(t.textContent); }
    else { const ta = document.createElement('textarea'); ta.value = t.textContent; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); ta.remove(); }
    setSockStatus('ÄÃ£ chÃ©p lá»‡nh â€” dÃ¡n vÃ o CMD/PowerShell trÃªn PC báº¡n.');
  } catch (_) { alert('Sao chÃ©p tháº¥t báº¡i â€” lá»‡nh: ' + t.textContent); }
};

$('btnDisconnect').onclick = () => getSocket().emit('disconnect-chrome');
$('btnReset').onclick = () => { if (confirm('XÃ³a toÃ n bá»™ dá»¯ liá»‡u?')) getSocket().emit('reset'); };

// Log toggle
// ===== Live game view (remote control) =====
let lastScreenT = 0;
let gameWin = null, gameMsgBound = false;

// Nháº­n káº¿t quáº£ tá»± soi tá»« tab web game (postMessage) vÃ  gá»­i lÃªn server
function bindGameMsg() {
  if (gameMsgBound) return;
  gameMsgBound = true;
  window.addEventListener('message', (e) => {
    if (!e.data || e.data.source !== 'tx-snip' || !Array.isArray(e.data.results)) return;
    if (gameWin && gameWin.closed) gameWin = null;
    if (gameWin && gameWin !== e.source) return;
    const s = getSocket();
    if (!s || !s.connected) return;
    s.emit('feed-results', { results: e.data.results }, (fed) => {
      const el = $('feedSrc');
      if (el) el.textContent = (fed > 0 ? 'Nháº­n ' + fed + ' vÃ¡n má»›i Â· ' : 'ÄÃ£ Ä‘á»“ng bá»™ Â· ') + new Date().toLocaleTimeString();
    });
  });
}

const live = $('liveView');
function ptr(e) {
  const r = live.getBoundingClientRect();
  const x = Math.max(0, Math.min(live.naturalWidth, (e.clientX - r.left) / r.width * live.naturalWidth));
  const y = Math.max(0, Math.min(live.naturalHeight, (e.clientY - r.top) / r.height * live.naturalHeight));
  return { x: Math.round(x), y: Math.round(y) };
}
['mousemove', 'mousedown', 'mouseup', 'dblclick'].forEach((tp) => {
  live.addEventListener(tp, (e) => {
    if (!live.dataset.ready) return;
    const p = ptr(e);
    const button = ['left', 'middle', 'right'][e.button] || 'left';
    if (tp === 'dblclick') {
getSocket().emit('screenInput', { type: 'click', x: p.x, y: p.y });
      getSocket().emit('screenInput', { type: 'click', x: p.x, y: p.y });
      getSocket().emit('screenInput', { type: tp, x: p.x, y: p.y, button });
    }
    e.preventDefault();
  });
});
live.addEventListener('wheel', (e) => {
  if (!live.dataset.ready) return;
  const p = ptr(e);
  getSocket().emit('screenInput', { type: 'wheel', x: p.x, y: p.y, deltaX: e.deltaX, deltaY: e.deltaY });
  e.preventDefault();
}, { passive: false });

// Cháº¡m trÃªn Ä‘iá»‡n thoáº¡i: cháº¡m = click táº¡i vá»‹ trÃ­ Ä‘Ã³
if (live) {
  live.addEventListener('touchstart', (e) => {
    if (!live.dataset.ready) return;
    e.preventDefault();
    const t = e.changedTouches[0];
    const r = live.getBoundingClientRect();
    const x = Math.round((t.clientX - r.left) / r.width * live.naturalWidth);
    const y = Math.round((t.clientY - r.top) / r.height * live.naturalHeight);
    getSocket().emit('screenInput', { type: 'click', x, y });
  }, { passive: false });
}

// GÃµ phÃ­m tá»« xa â€” chá»‰ khi vá»«a click vÃ o view game
live.tabIndex = 0;
live.addEventListener('mousedown', () => live.focus());
live.addEventListener('keydown', (e) => {
  if (!live.dataset.ready) return;
  const k = e.key;
  if (k === 'F12' || k === 'F5' || k === 'F11' || (e.ctrlKey && (k === 'r' || k === 'w' || k === 't' || k === 'u'))) return;
  if (k.length === 1) getSocket().emit('screenInput', { type: 'type', text: k });
  else getSocket().emit('screenInput', { type: 'key', key: k });
  e.preventDefault();
});

$('logToggle').onclick = () => {
  const box = $('logBox');
  const btn = $('logToggle');
  const open = box.classList.toggle('open');
  btn.innerHTML = '<span class="ms" style="font-size:15px">' + (open ? 'expand_less' : 'expand_more') + '</span> Nháº­t kÃ½ WS / sá»± kiá»‡n ' + (open ? '(áº©n)' : '(xem)');
};

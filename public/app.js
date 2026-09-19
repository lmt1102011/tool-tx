const $ = (id) => document.getElementById(id);
let socket = null;
let ownStatus = { connected: false, msg: '' };

// Giữ token/role trong sessionStorage để trang live.html mở từ popup dùng được (cùng origin Pages)
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

// ── Auto-discovery: launcher tự push link tunnel → server-url.json ──────
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
  // Nếu vừa tìm thấy URL mới mà chưa nối được → tự kết nối lại
  if (discoUrl && !(socket && socket.connected)) setTimeout(retryConnect, 400);
}
loadDiscovery();
setInterval(loadDiscovery, 30000);

// ── Server URL: localStorage("tx_server") → auto-discovery → config.js → same-origin ──
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

// Hiển thị lỗi kết nối trên statusLine (tool.html)
function setSockStatus(msg) {
  const el = $('statusLine');
  if (el) { el.textContent = msg; el.className = 'status err'; }
}

// Trạng thái phiên Chrome CDP RIÊNG của user (server gửi qua user-status)
function updateOwnUi() {
  const el = $('ownLine');
  if (el) {
    el.textContent = ownStatus.connected ? '✓ Chrome CDP của bạn đã sẵn sàng' : (ownStatus.msg || 'Chưa có phiên — nhấn KẾT NỐI TOOL');
    el.className = 'own-line' + (ownStatus.connected ? ' on' : '');
  }
}

// Mở màn hình 1:1 của chính mình trong tab/popup riêng
function openLivePopup() {
  if (window.__TX_TOKEN) {
    try { localStorage.setItem('tx_token', window.__TX_TOKEN); } catch (_) {}
    try { sessionStorage.setItem('tx_token', window.__TX_TOKEN); } catch (_) {}
  }
  if (window.__TX_ROLE) {
    try { localStorage.setItem('tx_role', window.__TX_ROLE); } catch (_) {}
  }
  const pop = window.open('live.html', 'txlive' + Date.now(), 'width=1310,height=780,resizable=yes,scrollbars=no,status=no');
  if (pop) pop.focus();
}

// Cập nhật ô "Server" trên thanh feed-note
function updateServerHost() {
  const sh = $('serverHost');
  if (!sh) return;
  const u = serverUrl();
  sh.textContent = (socket && socket.connected ? '' : '⚠ ') + (u || location.host);
}

// Tải socket.io-client từ server đã cấu hình (GitHub Pages không có /socket.io)
let ioLoad = null;
function ensureSocketIO() {
  if (window.io) return Promise.resolve();
  if (ioLoad) return ioLoad;
  ioLoad = new Promise((resolve, reject) => {
    const url = serverUrl() || location.origin;
    const s = document.createElement("script");
    s.src = url + "/socket.io/socket.io.js";
    s.onload = () => resolve();
    s.onerror = () => { ioLoad = null; reject(new Error("Không tải được socket.io từ " + url)); };
    document.head.appendChild(s);
  });
  return ioLoad;
}

let lastToken = null;
let lastAttemptUrl = "";
async function initSocket(authToken) {
  if (socket) return socket;
  lastToken = authToken || lastToken;
  // Đợi discovery server-url.json tối đa 1.5s (thường load xong trước auth)
  if (!discoLoaded) await new Promise(r => setTimeout(r, 1500));
  try {
    await ensureSocketIO();
  } catch (e) {
    log('Lỗi nạp socket.io: ' + e.message, 'err');
    setSockStatus('Lỗi kết nối — không đọc được socket.io từ "' + (serverUrl() || location.origin) + '". Bấm "đổi" ở feed-note hoặc kiểm tra server.');
    return null;
  }
  const url = serverUrl();
  lastAttemptUrl = url || "";
  socket = io(url || undefined, { auth: { token: lastToken }, transports: ['websocket', 'polling'] });
  window.socket = socket;
  bindSocketEvents();
  return socket;
}

// Tự nối lại khi URL server đổi (vd: launcher vừa push link tunnel mới)
function retryConnect() {
  if (!lastToken) return;
  const want = serverUrl() || "";
  if (want === lastAttemptUrl) return;
  if (socket) { try { socket.disconnect(); } catch (_) {} socket = null; }
  initSocket(lastToken);
}

function getSocket() { return socket; }
window.initSocket = initSocket;
window.getSocket = getSocket;

const STRAT_NAMES = {
  trendFollow: 'Đuổi xu hướng',
  reversal: 'Đảo chiều',
  patternMatch: 'Soi cầu',
  overloadReversal: 'Bão hòa',
  meanRevert: 'Cân bằng',
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
  else if (feeding) { badge.className = 'badge mid'; badge.textContent = 'SẴN SÀNG'; }
  else if (status.msg && status.msg.includes('Đang')) { badge.className = 'badge mid'; badge.textContent = 'CONNECTING'; }
  else { badge.className = 'badge off'; badge.textContent = 'OFFLINE'; }

  $('statusLine').textContent = status.msg || '';
  $('statusLine').className = 'status' + (status.msg && (status.msg.startsWith('Lỗi') || status.msg.includes('thất bại')) ? ' err' : '');
  if (mode === 'feed' && sockLive && !status.connected && !status.msg) {
    $('statusLine').textContent = hasData ? 'Đang nhận kết quả — ' + (history ? history.length : 0) + ' ván' : 'Server sẵn sàng — nhấn KẾT NỐI TOOL để mở phiên';
    $('statusLine').className = 'status';
  }
  $('btnDisconnect').disabled = !status.connected;

  // Grid luôn hiển thị; khi offline hiện placeholder thay vì ẩn hết
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
  if (srv) srv.textContent = (sockLive ? '' : '⚠ ') + (serverUrl() || location.host);
  const sv = $('setServer');
  if (sv) {
    sv.onclick = (e) => {
      e.preventDefault();
      const v = prompt('Địa chỉ server dự đoán (để trống = dùng mặc định):', serverUrl());
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
        const fs = $('feedSrc'); if (fs) fs.textContent = 'Đã chép plugin soi — dán vào Console tab web game';
      } catch (_) { alert('Copy thất bại — plugin: ' + bm); }
    };
  }

  if (!active) {
    const pb = $('predBox');
    pb.className = 'pred-box';
    const pbBadge = $('phaseBadge'); if (pbBadge) { pbBadge.textContent = 'CHỜ DỮ LIỆU'; pbBadge.className = 'phase-badge idle'; }
    const pbLine = $('phaseLine'); if (pbLine) { pbLine.textContent = 'chờ kết nối'; pbLine.className = 'phase-line g'; }
    $('predPick').textContent = '--';
    $('predPick').className = 'side';
    $('pctT').textContent = '50%';
    $('pctX').textContent = '50%';
    $('predConf').textContent = 'chờ kết nối';
    $('predAdvice').textContent = 'Nhấn KẾT NỐI TOOL — server mở/giữ phiên Chrome CDP soi bàn chung, mọi thiết bị cùng xem dự đoán';
    $('predAdvice').className = 'pred-advice off';
    $('predVotes').innerHTML = '';
    $('predLast').style.display = 'none';
    renderChips([]);
    $('statsList').innerHTML = '';
    $('accBig').textContent = '--';
    $('accBig').className = 'acc-big';
    $('accSub').textContent = '0 dự đoán';
    $('consensus').innerHTML = '';
    $('bestThresh').innerHTML = '';
    $('stratTable').innerHTML = '';
    $('biasNote').textContent = '';
    $('liveView').src = '';
    $('liveView').removeAttribute('data-ready');
    $('liveView').style.display = '';
    renderChart([], []);
    if ($('liveMask')) $('liveMask').style.display = '';
    if ($('liveMask')) $('liveMask').innerHTML = 'CHƯA CÓ HÌNH<br>' + (sockLive ? 'Đang chờ khung hình từ máy chủ' : 'Chưa kết nối server');
    return;
  }

  // Live view của bạn (Chrome CDP riêng theo user)
  const lc = $('liveCard');
  if (lc) lc.style.display = window.__TX_ROLE ? '' : 'none';
  updateOwnUi();

  // Live view diagnostics badge
  const sc = snap.screen || {};
  const liveB = $('liveBadge');
  if (liveB) {
    if (config && config.stream) {
      const age = sc.lastAt ? Math.round((Date.now() - sc.lastAt) / 100) / 10 + 's' : '--';
      if (sc.running) liveB.textContent = 'Ảnh: ' + sc.frames + ' frame · mới ' + age;
      else liveB.textContent = 'Ảnh: dừng' + (sc.lastErr ? ' (' + sc.lastErr + ')' : '');
      liveB.style.color = sc.running && sc.lastAt && Date.now() - sc.lastAt < 3000 ? '#22c55e' : (sc.running ? '#facc15' : '#ef4444');
    } else {
      liveB.textContent = 'Ảnh: TẮT';
      liveB.style.color = '#94a3b8';
    }
  }

  // ========== PREDICTION BOX ==========
  const pb = $('predBox');
  const hasResult = !!lastResult;
  const hasPrediction = !!prediction;

  // Phase badge/status (synced with the in-game overlay)
  const ph = snap.phase || 'IDLE';
  const phMap = { WAIT: ['wait', 'CHỜ PHIÊN MỚI'], ANALYZE: ['analyze', 'ĐANG PHÂN TÍCH'], READY: ['ready', hasPrediction && prediction.skip ? 'CÂN NHẮC' : 'CƯỢC!'], GET_RESULT: ['get', 'ĐANG LẤY KẾT QUẢ'], REVEAL: ['reveal', 'KẾT QUẢ'], IDLE: ['idle', 'CHỜ DỮ LIỆU'] };
  const [phCls, phTxt] = phMap[ph] || phMap.IDLE;
  const pbBadge = $('phaseBadge'), pbLine = $('phaseLine');
  pbBadge.className = 'phase-badge ' + phCls + (ph === 'READY' && hasPrediction && prediction.skip ? ' skips' : '');
  pbBadge.textContent = phTxt;
  pbLine.className = 'phase-line' + (ph === 'WAIT' || ph === 'GET_RESULT' ? ' y' : ph === 'IDLE' ? ' g' : '');
  pbLine.innerHTML = (ph === 'WAIT' || ph === 'ANALYZE' || ph === 'GET_RESULT') ? phTxt + '<span class="dot">...</span>' : (ph === 'REVEAL' && lastResult ? 'KẾT QUẢ: ' + (lastResult === 'T' ? 'TÀI' : 'XỈU') : (ph === 'IDLE' ? 'Chờ round mới...' : ''));

  // Reset border classes
  pb.className = 'pred-box' + (hasPrediction ? ' ready' : '');
  if (hasResult && lastWin !== null) {
    pb.className += lastWin ? ' win' : ' lose';
  }

  if (hasPrediction) {
    $('pctT').textContent = prediction.pT + '%';
    $('pctX').textContent = prediction.pX + '%';
    const pk = $('predPick');
    pk.textContent = prediction.pick === 'T' ? 'TÀI' : 'XỈU';
    pk.className = 'side ' + prediction.pick.toLowerCase();
    $('predConf').innerHTML = 'độ tin cậy <b>' + prediction.confidence + '%</b>';
    $('barT').style.width = prediction.pT + '%';
    $('barX').style.width = prediction.pX + '%';
  } else {
    $('pctT').textContent = '50%';
    $('pctX').textContent = '50%';
    $('predPick').textContent = '--';
    $('predPick').className = 'side';
    $('predConf').innerHTML = history && history.length >= 3 ? 'đợi dữ liệu...' : 'cần ≥3 ván';
    $('barT').style.width = '50%';
    $('barX').style.width = '50%';
  }

  // Advice line
  const adv = $('predAdvice');
  if (!prediction) { adv.textContent = ''; adv.className = 'pred-advice'; }
  else if (prediction.skip) { adv.textContent = 'Tin cậy thấp (' + prediction.confidence + '%) → NÊN BỎ VÁN'; adv.className = 'pred-advice warn'; }
  else if (prediction.kellyB <= 0) { adv.textContent = 'Lợi thế thấp → nên bỏ hoặc cược tối thiểu'; adv.className = 'pred-advice warn'; }
  else { adv.textContent = 'Kelly ' + prediction.kellyB + '% — cược ' + (prediction.pick === 'T' ? 'TÀI' : 'XỈU'); adv.className = 'pred-advice go'; }

  // Strategy votes (compact pills)
  const votes = prediction && prediction.votes ? prediction.votes : [];
  const vBox = $('predVotes');
  vBox.innerHTML = '';
  for (const v of votes) {
    const strat = stats && stats.strategyRates[v.name];
    const rate = strat ? strat.recentRate : '--';
    const p = document.createElement('span');
    p.className = 'pill';
    p.innerHTML = '<b>' + (STRAT_NAMES[v.name] || v.name) + '</b> → <span class="' + (v.pick === 'T' ? 'vt' : 'vx') + '">' + v.pick + '</span> ' + rate + '%';
    vBox.appendChild(p);
  }

  // Last result indicator
  const lastEl = $('predLast');
  if (hasResult && lastWin !== null) {
    lastEl.style.display = '';
    lastEl.innerHTML =
      'Kết quả: <span class="result ' + lastResult.toLowerCase() + '">' + (lastResult === 'T' ? 'TÀI' : 'XỈU') + '</span>' +
      (lastWin ? '<span class="outcome win">✓ ĐÚNG</span>' : '<span class="outcome lose">✗ SAI</span>');
  } else {
    lastEl.style.display = 'none';
  }

  // History chips
  renderChips(history ? history.slice(-30) : []);
  renderChart(snap.recentSums || [], history || []);

  // ========== STATS ==========
  if (stats) {
    // Summary stats
    const streak = stats.currentStreak ? (stats.currentStreak.side === 'T' ? 'TÀI' : 'XỈU') + ' ×' + stats.currentStreak.len : '--';
    const sums = snap.recentSums || [];
    const avgSum = sums.length ? Math.round((sums.reduce((a, b) => a + b, 0) / sums.length) * 10) / 10 : '--';
    $('statsList').innerHTML = [
      ['Tổng', stats.total],
      ['TÀI', stats.t, 't'],
      ['XỈU', stats.x, 'x'],
      ['Tỷ lệ T', stats.tRate + '%'],
      ['TB tổng (12 ván)', avgSum],
      ['Chuỗi hiện tại', streak],
      ['Chuỗi dài nhất', stats.longestStreak],
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
    $('accSub').textContent = stats.predictionCount + ' dự đoán · ' + (stats.strategyRates.trendFollow ? stats.strategyRates.trendFollow.total : 0) + ' mẫu luyện';

    // Consensus bar (how many strategies agree with main pick)
    const votesArr = prediction && prediction.votes ? prediction.votes : [];
    if (votesArr.length > 0 && prediction) {
      const agree = votesArr.filter(v => v.pick === prediction.pick).length;
      const total = votesArr.length;
      $('consensus').innerHTML = Array.from({length: 5}, (_, i) =>
        '<div class="bar' + (i < agree ? ' on' : '') + '"></div>'
      ).join('') + '<span style="font-size:10px;color:var(--dim);margin-left:4px">' + agree + '/' + total + ' đồng thuận</span>';
    } else {
      $('consensus').innerHTML = '';
    }

    // Best threshold
    const bt = stats.bestThreshold;
    $('bestThresh').innerHTML = bt && bt.total > 0
      ? '<div style="font-size:11px;color:var(--dim)">Ngưỡng tối ưu: <b style="color:var(--text)">' + bt.t + '% tin cậy</b> → hit ' + bt.rate + '% (' + bt.total + ' ván)</div>'
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
      bn.textContent = '⚠ BIAS: ' + b.recentN + ' ván gần nghiêng về ' + (b.side === 'T' ? 'TÀI' : 'XỈU') + ' (z=' + b.z + ')';
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
    svg.innerHTML = '<text x="140" y="85" fill="#64748b" font-size="11" text-anchor="middle">Chưa đủ dữ liệu</text>';
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
  if (lastSum > prevSum + 1.5) { trendCls = 'up'; trendText = '▲ TÀI ⇧'; }
  else if (lastSum < prevSum - 1.5) { trendCls = 'down'; trendText = '▼ XỈU ⇩'; }
  else { trendCls = 'flat'; trendText = '→ Đi ngang'; }
  trendEl.className = 'trend-tag ' + trendCls;
  trendEl.innerHTML = '<span class="ms">' + (trendCls === 'up' ? 'trending_up' : trendCls === 'down' ? 'trending_down' : 'trending_flat') + '</span> ' + trendText;
}

// ===== Socket events =====
function bindSocketEvents() {
  socket.on('snapshot', render);
  socket.on('connect', () => {
    const u = serverUrl();
    log('Đã kết nối server: ' + (u || 'cùng nguồn'));
    updateServerHost();
    setSockStatus('Đã kết nối — ' + (u || location.host));
    if (window.__TX_ROLE && launchOnReady) { launchOnReady = false; socket.emit('launch-profile', {}); }
  });
  socket.on('disconnect', (reason) => {
    log('Mất kết nối: ' + reason, 'err');
    updateServerHost();
    setSockStatus('Mất kết nối server — ' + reason);
    loadDiscovery(); // tunnel có thể vừa restart → lấy URL mới ngay
  });
  socket.on('connect_error', (err) => {
    const u = serverUrl() || location.origin;
    log('Lỗi kết nối: ' + (err.message || err), 'err');
    updateServerHost();
    // Override tay đang trỏ URL chết mà auto-discovery có URL khác → tự quên override và thử lại
    const ov = getServerOverride();
    if (ov && discoUrl && ov !== discoUrl) {
      setSockStatus('Lỗi kết nối "' + u + '" — đang chuyển về server tự động "' + discoUrl + '"...');
      try { localStorage.removeItem('tx_server'); } catch (_) {}
      if (socket) { try { socket.disconnect(); } catch (_) {} socket = null; }
      initSocket(lastToken);
      return;
    }
    setSockStatus('Lỗi kết nối "' + u + '" — ' + (err.message || 'kiểm tra server đã bật chưa') + '. Đang tự tìm server...');
    loadDiscovery(); // lấy ngay URL tunnel mới nhất nếu server-url.json vừa đổi
  });
  socket.on('user-status', (d) => {
    ownStatus = (d && typeof d === 'object') ? d : { connected: false, msg: '' };
    updateOwnUi();
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
      log('Đang mở Chrome CDP riêng của bạn...');
      setSockStatus('Đang mở Chrome CDP của bạn...');
      s.emit('launch-profile', {});
    } else {
      log('Chưa đăng nhập — đăng nhập để tạo phiên Chrome CDP riêng.', 'err');
      setSockStatus('Đăng nhập trước khi dùng KẾT NỐI.');
    }
    return;
  }
  if (!s && window.__TX_TOKEN && typeof initSocket === 'function') {
    launchOnReady = !!role;
    log(launchOnReady ? 'Đang kết nối server — sẽ tự mở phiên Chrome CDP của bạn...' : 'Đang kết nối server...');
    setSockStatus('Đang kết nối server...');
    initSocket(window.__TX_TOKEN);
  }
};
const bol = $('btnOpenLive');
if (bol) bol.onclick = () => openLivePopup();
$('btnDisconnect').onclick = () => getSocket().emit('disconnect-chrome');
$('btnReset').onclick = () => { if (confirm('Xóa toàn bộ dữ liệu?')) getSocket().emit('reset'); };

// Log toggle
// ===== Live game view (remote control) =====
let lastScreenT = 0;
let gameWin = null, gameMsgBound = false;

// Nhận kết quả tự soi từ tab web game (postMessage) và gửi lên server
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
      if (el) el.textContent = (fed > 0 ? 'Nhận ' + fed + ' ván mới · ' : 'Đã đồng bộ · ') + new Date().toLocaleTimeString();
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

// Chạm trên điện thoại: chạm = click tại vị trí đó
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

// Gõ phím từ xa — chỉ khi vừa click vào view game
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
  btn.innerHTML = '<span class="ms" style="font-size:15px">' + (open ? 'expand_less' : 'expand_more') + '</span> Nhật ký WS / sự kiện ' + (open ? '(ẩn)' : '(xem)');
};

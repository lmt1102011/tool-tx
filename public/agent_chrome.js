#!/usr/bin/env node
// agent_chrome.js — chạy tại PC của BẠN.
// Mở Chrome CDP ngay trên máy bạn, nối outbound tới tool server, đọc kết quả game từ đó.
// Dùng:
//   node agent_chrome.js --server <URL-SERVER> --code <MA-LIEN-KET>
// Không cãn cài thêm gì (Node 22+). Nếu máy chưa có Node: https://nodejs.org

const os = require('os');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

const argMap = {};
process.argv.slice(2).forEach((a, i, arr) => {
  if (a.startsWith('--')) {
    const n = a.slice(2);
    const v = arr[i + 1] && !arr[i + 1].startsWith('--') ? arr[i + 1] : '';
    argMap[n] = v;
  }
});

const log = (...x) => console.log(new Date().toISOString().slice(11, 19), ...x);
const SERVER = String(argMap.server || '').trim().replace(/\/+$/, '');
const CODE = String(argMap.code || '').trim().toUpperCase();
if (!SERVER || !CODE) {
  console.log('Cách dùng: node agent_chrome.js --server <URL-SERVER> --code <MA6SO>');
  console.log('Ví dụ:      node agent_chrome.js --server https://abc.trycloudflare.com --code ABC123');
  process.exit(1);
}
if (typeof WebSocket !== 'function') {
  console.log('Cần Node 22+. Cài từ https://nodejs.org rồi chạy lại.');
  process.exit(1);
}

const profileDir = path.join(os.tmpdir(), 'tx-agent-' + CODE);

function chromePath() {
  const list = [
    process.env.CHROME_PATH,
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/usr/bin/google-chrome', '/usr/bin/microsoft-edge', '/usr/bin/chromium', '/usr/bin/chromium-browser',
  ];
  for (const c of list) { if (c && c.trim() && fs.existsSync(c)) return c; }
  return null;
}

const wait = (ms) => new Promise((r) => setTimeout(r, ms));
async function waitFor(fn, ms, step) { const t = Date.now(); while (Date.now() - t < ms) { const v = await fn(); if (v) return v; await wait(step || 250); } return null; }

// ── 1) Mở Chrome CDP local ──
const exe = chromePath();
if (!exe) {
  console.log('Không tìm thấy Chrome/Edge trên máy này. Cài Chrome rồi chạy lại.');
  process.exit(1);
}

let chromeDevtoolsUrl = '';
let chromeProc = null;
let closing = false;

function spawnChrome() {
  const argsC = [
    '--remote-debugging-port=0',
    '--remote-debugging-address=127.0.0.1',
    '--remote-allow-origins=*',
    '--user-data-dir=' + profileDir,
    '--no-first-run',
    '--no-default-browser-check',
    '--disable-breakpad',
    '--no-crash-bubble',
    '--window-size=1000,650',
    'about:blank',
  ];
  chromeProc = spawn(exe, argsC, { stdio: ['ignore', 'ignore', 'pipe'] });
  chromeProc.stderr.on('data', (d) => {
    const m = String(d).match(/ws:\/\/127\.0\.0\.1:(\d+)\/devtools\/browser\/(\S+)/);
    if (m && !chromeDevtoolsUrl) chromeDevtoolsUrl = 'ws://127.0.0.1:' + m[1] + '/devtools/browser/' + m[2];
  });
  chromeProc.on('error', (e) => { if (!closing) console.log('Lỗi mở Chrome:', e.message); });
  chromeProc.on('exit', (c) => {
    if (!closing) {
      console.log('Chrome đã bị đóng (code ' + c + '). Tắt agent...');
      try { process.exit(0); } catch (_) {}
    }
  });
}
spawnChrome();
process.on('exit', () => { closing = true; try { if (chromeProc) chromeProc.kill(); } catch (_) {} });

(async () => {
  chromeDevtoolsUrl = await waitFor(() => chromeDevtoolsUrl, 40000);
  if (!chromeDevtoolsUrl) { console.log('Chrome 30s chưa bật CDP — đóng hết Chrome đang chạy rồi thử lại.'); process.exit(1); }
  log('Chrome CDP: ' + chromeDevtoolsUrl);

  // ── 2) CDP client (browser-level ws) ──
  let cdpws = null;
  let cdpId = 0;
  const pending = new Map();
  let cdpReadyP = null;
  const cdpReady = new Promise((resolve, reject) => {
    cdpReadyP = { resolve, reject };
  });

  function cdpSend(method, params, sessionId) {
    return new Promise((resolve, reject) => {
      if (!cdpws || cdpws.readyState !== 1) { reject(new Error('CDP chưa kết nối')); return; }
      const id = ++cdpId;
      const msg = { id, method, params: params || {} };
      if (sessionId) msg.sessionId = sessionId;
      pending.set(id, { resolve, reject });
      setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('CDP timeout: ' + method)); } }, 25000);
      try { cdpws.send(JSON.stringify(msg)); } catch (e) { pending.delete(id); reject(e); }
    });
  }

  cdpws = new WebSocket(chromeDevtoolsUrl);
  cdpws.onopen = () => { try { cdpReadyP.resolve(); } catch (_) {} log('CDP sẵn sàng.'); };
  cdpws.onerror = () => { console.log('Lỗi WebSocket CDP Chrome.'); };
  cdpws.onclose = () => { try { cdpReadyP.reject(new Error('CDP đóng')); } catch (_) {} };
  cdpws.onmessage = (ev) => {
    let m;
    try { m = JSON.parse(ev.data); } catch (_) { return; }
    if (m.id) {
      const p = pending.get(m.id);
      if (p) {
        pending.delete(m.id);
        if (m.error) p.reject(new Error(m.error.message || JSON.stringify(m.error)));
        else p.resolve(m.result || {});
      }
    }
  };
  await cdpReady;

  // ── 3) Theo dõi tab game Sunwin ──
  let gameHost = '';
  let gameUrl = '';
  let gameTargetId = null;
  let gameSessionId = null;
  let navBusy = false;

  function hostOf(url) {
    try { return String(new URL(url).hostname || '').replace(/^www\./, ''); } catch (_) { return ''; }
  }

  async function ensureGameTab(url) {
    if (!url || navBusy) return;
    navBusy = true;
    try {
      const host = hostOf(url);
      if (host) gameHost = host;
      const { targetInfos } = await cdpSend('Target.getTargets');
      let t = (targetInfos || []).find((x) => x.type === 'page' && x.url && host && hostOf(x.url) === host);
      if (!t) {
        const created = await cdpSend('Target.createTarget', { url });
        t = { targetId: created.targetId };
        await wait(400);
      }
      gameTargetId = t.targetId;
      const attached = await cdpSend('Target.attachToTarget', { targetId: gameTargetId, flatten: true });
      gameSessionId = attached.sessionId;
      if (!String(t.url || '').length || hostOf(t.url || '') !== host) {
        await cdpSend('Page.navigate', { url }, gameSessionId).catch(() => {});
      }
      log('Tab game sẵn sàng. target=' + String(gameTargetId).slice(0, 6));
    } catch (e) {
      console.log('Lỗi mở tab game: ' + e.message);
    } finally {
      navBusy = false;
    }
  }

  async function evalInGame(expr) {
    if (!gameTargetId) throw new Error('Chưa có tab game.');
    if (!gameSessionId) {
      const att = await cdpSend('Target.attachToTarget', { targetId: gameTargetId, flatten: true });
      gameSessionId = att.sessionId;
    }
    const res = await cdpSend('Runtime.evaluate', {
      expression: expr,
      awaitPromise: true,
      returnByValue: true,
      userGesture: true,
    }, gameSessionId);
    if (res && res.exceptionDetails) throw new Error('JS: ' + ((res.exceptionDetails.exception && res.exceptionDetails.exception.description) || 'lỗi'));
    return res && res.result ? res.result.value : undefined;
  }

  // ── 4) Kết nối server (outbound) ──
  function wsUrlFor(s) {
    return (s.indexOf('https://') === 0 ? 'wss://' : 'ws://') + s.replace(/^https?:\/\//, '') + '/agent-ws';
  }

  function connectServer() {
    const url = wsUrlFor(SERVER);
    log('Nối server: ' + SERVER + ' (mã ' + CODE + ')');
    let serverWs;
    try {
      serverWs = new WebSocket(url);
    } catch (e) {
      console.log('Lỗi tạo WebSocket: ' + e.message);
      setTimeout(connectServer, 5000);
      return;
    }
    serverWs.onopen = () => { try { serverWs.send(JSON.stringify({ t: 'hello', code: CODE, v: 1, node: process.version.slice(1) })); } catch (_) {} };
    serverWs.onclose = () => {
      log('Mất kết nối server — thử lại trong 5s...');
      setTimeout(connectServer, 5000);
    };
    serverWs.onerror = () => { console.log('Lỗi kết nối server.'); };
    serverWs.onmessage = (ev) => {
      let m;
      try { m = JSON.parse(ev.data); } catch (_) { return; }
      if (!m || !m.t) return;
      if (m.t === 'ok') {
        log('Server xác nhận: uid=' + String(m.uid || '').slice(0, 8) + (m.url ? ' — mở game...' : ''));
        if (m.url) { gameUrl = m.url; ensureGameTab(m.url).catch(() => {}); }
      } else if (m.t === 'err') {
        console.log('Server từ chối: ' + m.message);
        try { process.exit(1); } catch (_) {}
      } else if (m.t === 'eval') {
        Promise.resolve().then(async () => {
          try {
            if (!gameTargetId) {
              throw new Error('Chưa có tab game — chờ server gửi link mở.');
            }
            const value = await evalInGame(String(m.expr || ''));
            try { serverWs.send(JSON.stringify({ t: 'res', id: m.id, value })); } catch (_) {}
          } catch (e) {
            try { serverWs.send(JSON.stringify({ t: 'res', id: m.id, error: (e && e.message) || String(e) })); } catch (_) {}
          }
        });
      } else if (m.t === 'ping') {
        try { serverWs.send(JSON.stringify({ t: 'pong', ts: Date.now() })); } catch (_) {}
      }
    };
    setTimeout(() => { try { serverWs.send(JSON.stringify({ t: 'ping', ts: Date.now() })); } catch (_) {} }, 15000);
  }

  connectServer();
  setInterval(() => {
    if (gameUrl) ensureGameTab(gameUrl).catch(() => {});
  }, 60000);

  console.log('Agent đang chạy. Đừng đóng cửa sổ này. (Ctrl+C để dừng)');
})();
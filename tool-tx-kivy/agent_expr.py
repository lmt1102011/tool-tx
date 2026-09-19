# agent_expr.py — biểu thức JS đọc kết quả game từ trong tab Sunwin.
# Giống hệt buildResultsExpr trong lib/scraper.js (server dùng) để agent python
# đọc cùng một thứ, nuôi predictor theo bàn của chính user.

_COLLECT_FN = r"""
function collect() {
  const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
  const toSide = (t) => {
    if (t.includes('tài')) return 'T';
    if (t.includes('xỉu') || t.includes('xiu')) return 'X';
    return null;
  };
  const chips = [];
  for (const s of (sel || [])) {
    document.querySelectorAll(s).forEach((el) => {
      const r = toSide(normalize(el.textContent));
      if (r) chips.push({ el, r });
    });
  }
  if (chips.length === 0) {
    const ownText = (el) => {
      let s = '';
      el.childNodes.forEach((n) => {
        if (n.nodeType === Node.TEXT_NODE) s += n.textContent;
      });
      return s;
    };
    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_ELEMENT);
    let node;
    while ((node = walker.nextNode())) {
      const own = normalize(ownText(node));
      const r = toSide(own);
      if (r && own.length <= 8) chips.push({ el: node, r });
    }
  }
  const containers = new Set();
  for (const c of chips) {
    let e = c.el.parentElement;
    for (let i = 0; e && i < 6; i++) {
      containers.add(e);
      e = e.parentElement;
    }
  }
  const sumNodes = [];
  if (containers.size > 0) {
    const textWalker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = textWalker.nextNode())) {
      const v = normalize(n.textContent);
      if (/^\d{1,2}$/.test(v) && v.length >= 1) {
        const num = parseInt(v, 10);
        if (num >= 3 && num <= 18) {
          let a = n.parentElement;
          let hit = false;
          for (let i = 0; a && i < 8; i++) {
            if (containers.has(a)) { hit = true; break; }
            a = a.parentElement;
          }
          if (hit) sumNodes.push(num);
        }
      }
    }
  }
  const tokens = [];
  for (const c of chips) tokens.push(c.r);
  for (const s of sumNodes) tokens.push(String(s));
  const seen = [];
  for (const tk of tokens.slice(-400)) {
    if (seen.length === 0 || seen[seen.length - 1] !== tk) seen.push(tk);
  }
  return seen;
}
"""


import json


def build_results_expr(selectors=None):
    return "(function(sel){" + _COLLECT_FN + ";return collect();})(" + json.dumps(selectors or [], ensure_ascii=False) + ")"
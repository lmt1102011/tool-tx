import { initializeApp } from "https://www.gstatic.com/firebasejs/10.12.2/firebase-app.js";
import {
  getAuth,
  setPersistence,
  browserLocalPersistence,
  signInWithEmailAndPassword,
  onAuthStateChanged,
  signOut,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-auth.js";
import {
  getDatabase,
  ref,
  get,
  set,
  update,
  remove,
  query,
  orderByChild,
  equalTo,
  onValue,
} from "https://www.gstatic.com/firebasejs/10.12.2/firebase-database.js";

const firebaseConfig = {
  apiKey: "AIzaSyCN8VEuBWsnXrZqSWJYrFkZd7ckdFIqbCg",
  authDomain: "tool-tx-by-lmt.firebaseapp.com",
  databaseURL: "https://tool-tx-by-lmt-default-rtdb.firebaseio.com",
  projectId: "tool-tx-by-lmt",
  storageBucket: "tool-tx-by-lmt.firebasestorage.app",
  messagingSenderId: "848516918996",
  appId: "1:848516918996:web:37774fde1937d1ef361541",
  measurementId: "G-YDDCEKPGYC",
};

const app = initializeApp(firebaseConfig);
export const auth = getAuth(app);
try { setPersistence(auth, browserLocalPersistence); } catch (_) {}
export const db = getDatabase(app);

export async function tryReauthSaved() {
  let raw = null;
  try { raw = sessionStorage.getItem("tx_pending"); } catch (_) {}
  if (!raw) return false;
  let v = null;
  try { v = JSON.parse(raw); } catch (_) {}
  if (!v || !v.u || !v.p) return false;
  try {
    await signInWithEmailAndPassword(auth, emailForUsername(v.u), v.p);
    try { sessionStorage.removeItem("tx_pending"); } catch (_) {}
    return true;
  } catch (_) { return false; }
}

export function doc(fdb, ...path) {
  return ref(fdb, path.join("/"));
}

export async function getDoc(r) {
  const s = await get(r);
  return { exists: () => s.exists(), data: () => (s.exists() ? s.val() : null) };
}

export function setDoc(r, value, opts) {
  return opts && opts.merge ? update(r, value) : set(r, value);
}

export function updateDoc(r, value) {
  return update(r, value);
}

export function deleteDoc(r) {
  return remove(r);
}

export function onSnapshot(r, cb) {
  return onValue(r, (snap) => cb({ exists: () => snap.exists(), data: () => (snap.exists() ? snap.val() : null) }));
}

export function emailForUsername(username) {
  return String(username || "").trim().toLowerCase().replace(/\s+/g, "") + "@tooltx.app";
}

export async function getUserByUsername(username) {
  const uname = String(username || "").trim().toLowerCase();
  if (!uname) return null;
  const r = query(ref(db, "users"), orderByChild("username"), equalTo(uname));
  const snap = await get(r);
  const v = snap.val();
  if (!v) return null;
  const keys = Object.keys(v);
  return { id: keys[0], data: v[keys[0]] };
}

export async function loginByUsername(username, password) {
  const uname = String(username || "").trim().toLowerCase();
  if (!uname || !password) throw new Error("Nhập đầy đủ tài khoản và mật khẩu");
  const email = emailForUsername(uname);
  let cred;
  try {
    cred = await signInWithEmailAndPassword(auth, email, password);
  } catch (e) {
    throw new Error(msgFire(e));
  }
  const snap = await get(ref(db, "users/" + cred.user.uid));
  if (!snap.exists()) { await signOut(auth); throw new Error("Tài khoản không tồn tại"); }
  const data = snap.val();
  if (data.role === "disabled") { await signOut(auth); throw new Error("Tài khoản đã bị khóa"); }
  try { sessionStorage.setItem("tx_pending", JSON.stringify({ u: uname, p: password })); } catch (_) {}
  return { uid: cred.user.uid, data };
}

export async function registerUser(username, password, displayName, balanceFields) {
  const uname = String(username || "").trim().toLowerCase();
  if (!/^[a-z0-9._-]{3,20}$/.test(uname))
    throw new Error("Username chỉ gồm chữ thường/số, 3–20 ký tự");
  if ((password || "").length < 6) throw new Error("Mật khẩu ít nhất 6 ký tự");
  const email = emailForUsername(uname);
  const prevUser = auth.currentUser;
  let j;
  try {
    const res = await fetch(
      "https://identitytoolkit.googleapis.com/v1/accounts:signUp?key=" + firebaseConfig.apiKey,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password, returnSecureToken: true }),
      }
    );
    j = await res.json();
  } catch (e) {
    throw new Error("Mất kết nối Firebase: " + ((e && e.message) || ""));
  }
  if (j.error) {
    if (/EMAIL_EXISTS/i.test(j.error.message || ""))
      throw new Error("Username này đã được đăng ký");
    throw new Error(msgFire(j.error));
  }
  const uid = j.localId;
  let isAdmin = false;
  try {
    if (prevUser) {
      const s = await getDoc(doc(db, "users/" + prevUser.uid));
      isAdmin = !!s.exists() && s.data().role === "admin";
    }
  } catch (_) {}
  const now = Date.now();
  const data = {
    username: uname,
    email,
    displayName: (displayName || "").trim() || uname,
    role: "user",
    balanceFields: isAdmin ? Math.max(0, Math.floor(Number(balanceFields) || 0)) : 0,
    createdAt: now,
    lastSeen: now,
  };
  try {
    const authQ = isAdmin ? (await prevUser.getIdToken()) : j.idToken;
    const r = await fetch(
      firebaseConfig.databaseURL + "/users/" + uid + ".json?auth=" + authQ,
      {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data),
      }
    );
    if (!r.ok) {
      const t = await r.text().catch(() => "");
      throw new Error("Ghi dữ liệu thất bại: " + (t || r.status));
    }
  } catch (e) {
    if (/(Ghi dữ liệu)/.test(e.message || "")) throw e;
    throw new Error("Ghi dữ liệu thất bại (kiểm tra rules Realtime Database)");
  }
  if (!prevUser) {
    try { await signInWithEmailAndPassword(auth, email, password); } catch (_) {}
  }
  return { uid };
}

export function msgFire(e) {
  const m = (e && (e.message || e.code) || "").toString();
  if (/email-already-in-use/i.test(m)) return "Email đã được sử dụng";
  if (/wrong-password|invalid-credential/i.test(m)) return "Sai mật khẩu";
  if (/user-not-found/i.test(m)) return "Tài khoản không tồn tại";
  if (/invalid-email/i.test(m)) return "Địa chỉ email không hợp lệ";
  if (/weak-password/i.test(m)) return "Mật khẩu quá yếu";
  if (/too-many-requests/i.test(m)) return "Quá nhiều lần thử, hãy đợi vài phút";
  if (/permission denied|denied/i.test(m)) return "Chưa cấp quyền trên Realtime Database (rules)";
  return m || "Có lỗi xảy ra";
}

export async function getRate() {
  try {
    const s = await getDoc(doc(db, "settings/config"));
    if (s.exists()) return Number(s.data().vndPerPick) || 5000;
  } catch (_) {}
  return 5000;
}

export function formatTime(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  if (h > 0) return `${h} giờ ${m} phút`;
  if (m > 0) return `${m} phút ${ss}s`;
  return `${ss}s`;
}

export function formatClock(sec) {
  const s = Math.max(0, Math.floor(Number(sec) || 0));
  const p = (x) => String(x).padStart(2, "0");
  const hh = String(Math.floor(s / 3600)).padStart(2, "0");
  if (hh === "00") return `${p(Math.floor((s % 3600) / 60))}:${p(s % 60)}`;
  return `${hh}:${p(Math.floor((s % 3600) / 60))}:${p(s % 60)}`;
}

export function formatMoney(amount) {
  return Number(amount || 0).toLocaleString("vi-VN") + " VNĐ";
}

export function formatPicks(n) {
  return Number(n || 0).toLocaleString("vi-VN") + " lượt đoán";
}

export function picksForMoney(moneyVnd, price) {
  return Math.max(0, Math.floor(Math.max(0, moneyVnd || 0) / (price || 5000)));
}

export function moneyForPicks(picks, price) {
  return Math.max(0, Math.round((Math.max(0, picks || 0) * (price || 5000))));
}

export function moneyFor(sec, rate) {
  return Math.round((Math.max(0, sec || 0) / 3600) * (rate || 10000));
}

export function secsForMoney(moneyVnd, rate) {
  return Math.round((Math.max(0, moneyVnd || 0) / (rate || 10000)) * 3600);
}

// Quy đổi dữ liệu cũ: balanceSeconds (giây) → balanceFields (lượt đoán). 1 lượt ≈ 60 giây.
export function migratePicks(data) {
  const c = data && data.balanceFields;
  if (c !== undefined && c !== null) return Math.max(0, Math.floor(Number(c) || 0));
  const sec = Number((data && data.balanceSeconds) || 0);
  if (sec > 0) return Math.max(1, Math.floor(sec / 60));
  return 0;
}

export async function requireUser() {
  const u = auth.currentUser;
  if (!u) throw new Error("no-auth");
  const s = await getDoc(doc(db, "users/" + u.uid));
  if (!s.exists()) {
    await signOut(auth);
    throw new Error("deleted");
  }
  return { uid: u.uid, username: (u.email || "").split("@")[0], data: s.data() };
}

export function showToast(msg, ms) {
  const el = document.getElementById("toast");
  if (!el) return;
  el.textContent = msg;
  el.classList.add("show");
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove("show"), ms || 2500);
}

export function setAvatar(el, name) {
  const n = String(name || "?").trim();
  const letter = (n.charAt(0) || "?").toUpperCase();
  let h = 0;
  for (let i = 0; i < n.length; i++) h = (h * 31 + n.charCodeAt(i)) >>> 0;
  const k = (h % 8) + 1;
  el.textContent = letter;
  el.className = "avatar av" + k;
}

export { ref, get, update, onValue, signOut, onAuthStateChanged };
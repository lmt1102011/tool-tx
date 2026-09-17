// ── Cấu hình frontend (chạy trên GitHub Pages hoặc cục bộ) ──────────
// __TX_SERVER: địa chỉ server dự đoán do ADMIN chạy.
//   - Để "" khi mở tool TRỰC TIẾP từ server (localhost:8787) → tự kết nối cùng nguồn.
//   - Khi deploy lên GitHub Pages, điền địa chỉ công khai của admin:
//     VD: "http://203.0.113.10:8787" hoặc "https://tx.tool-demo.workers.dev"
// Người dùng có thể đổi nhanh bằng cách bấm "Server" trên trang tool (lưu localStorage).
window.__TX_SERVER = "";
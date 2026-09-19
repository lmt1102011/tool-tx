# Tool TX — App KivyMD

App đăng nhập/đăng ký (dùng đúng tài khoản như web `lmt1102011.github.io/tool-tx`) +
hiển thị dự đoán Tài/Xỉu từ server; trên **máy tính** còn mở được **Chrome/Chromium
CDP tại máy của bạn** (mượt tuyệt đối, không stream qua server).

## Cài đặt & chạy trên máy tính

Cần Python 3.10–3.13 (Kivy chưa hỗ trợ 3.14).

```
pip install -r requirements.txt
python main.py
```

Màn hình:
- **ĐĂNG NHẬP / ĐĂNG KÝ** — giống web (Firebase Auth: `username@tooltx.app`).
- **HOME** — nút **KHỞI ĐỘNG CHROME MÁY BẠN**: lấy mã liên kết, mở chrome/edge/chromium
  trên máy, nối `/agent-ws` tới server, tự đọc kết quả bàn game của bạn → dự đoán bàn riêng.
- **TÀI KHOẢN** — username, lượt đoán (balanceFields).

> `.bat`/`.js` cũ dành cho máy không có Python: dùng `agent_chrome.bat` trên web.
> App Python dùng chính giao thức CDP chuẩn nên chạy được Chrome, Edge, **Chromium**,
> Brave, Vivaldi, Opera. Ghi đè bằng biến `CHROME_PATH` hoặc gọi `find_browser(path)`.

Thử nhanh không cần GUI:

```
python -c "from agent import find_browser; print(find_browser())"
python -c "import fb; print(fb.email_for('tinhyeu'))"
```

## Build file APK (Android)

Buildozer **chỉ chạy trên Linux** — dùng WSL2 (Ubuntu) hoặc máy Linux:

```
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev \
  libncurses5-dev libncursesw5-dev libtinfo6 libffi-dev libssl-dev python3-pip
pip install --user buildozer cython
cd tool-tx-kivy
buildozer init          # giữ buildozer.spec đã có
buildozer android debug # -> bin/tooltx-1.0.0-*.apk
```

APK sau build:
- Đăng nhập/đăng ký + kết nối socket.io nhận dự đoán: **hoạt động**.
- **Không mở được Chrome/CDP trên Android** (hệ điều hành không cho) — nút đó hiện
  thông báo + in mã liên kết để chạy trên máy tính.

## Chạy hoàn toàn trên điện thoại — nút START BROWSER (Chromium Fork)

Nguyên tắc: bạn tự build 1 **fork Chromium** có DevTools TCP chạy sẵn
`127.0.0.1:9222` (Chrome/WebView chính thức **không** làm được điều này trên Android).
Python APK chỉ việc mở fork bằng intent rồi `hcdp.py` bắt CDP ngay trong máy — không PC,
không ADB, không server trung gian lúc dùng.

```
ToolTX APK ──http──▶ http://127.0.0.1:9222/json/version
        └──ws──┐    ▼
               │  Chromium Fork (tab Sunwin hiện trên màn hình điện thoại)
               └──CDP──▶ Cookie/Login/DOM/JS ▶ Sunwin
```

1. **Fork**: chạy `fork/build.sh` **một lần trên Linux/WSL** (30–90GB đĩa, 16GB+ RAM).
   Patch CDP always-on theo `fork/PATCH.md`. Ra `ChromePublic.apk` → ký → cài.
2. **Cài ToolTX APK** (buildozer như trên). Lần đầu vào nút **START BROWSER**:
   mở fork, hcdp tự nối CDP, chuyển 1 tab riêng đến Sunwin (đăng nhập tay lần đầu,
   login nằm trong profile fork).
3. **Số lượt do server quản lý như web**: app đọc `balanceFields` từ Firebase khi vào
   HOME và định kỳ mỗi 30s; khi hết lượt (`picks<=0`, không phải admin) hiện
   "HẾT LƯỢT ĐOÁN" và chặn khởi động.
4. Sau verif đầu, để tránh Doze tắt fork: bật giữ màn hình sáng (`FLAG_KEEP_SCREEN_ON`).

Lưu ý Play Store sẽ từ chối app có CDP loopback điều khiển browser; dùng sideload cá nhân.

## Cấu trúc

| File | Vai trò |
|------|---------|
| `fb.py` | Firebase Auth REST (login/register/refresh) + Realtime Database, session file |
| `sio_client.py` | socket.io client (snapshot, panel-push, user-status, mã agent) + tự tìm server |
| `agent.py` | Agent: spawn browser desktop **hoặc** dùng `cdp_backend` (fork Android) + WS `/agent-ws` |
| `hcdp.py` | CDP controller Android: `ForkCdpBridge` (wait_ready/ensure_game_tab/eval), `start_browser` |
| `agent_expr.py` | Biểu thức JS đọc kết quả (giống `lib/scraper.js` server) |
| `main.py` + `ui.kv` | Giao diện KivyMD + quản lý số lượt (picks) + nút START BROWSER |
| `fork/build.sh` | Build Chromium fork (Linux/WSL, 1 lần) |
| `fork/PATCH.md` | Patch nguồn Chromium bật DevTools TCP 9222 always-on |
| `config.txt` | (tùy chọn) `{"server": "http://..."}` ghi đè server tự động |
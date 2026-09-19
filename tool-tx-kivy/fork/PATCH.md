# PATCH.md — Bật DevTools TCP 9222 ALWAYS-ON trong Chromium fork

Mục đích: Python APK (ToolTX) phải gọi được
`http://127.0.0.1:9222/json/version` ngay khi mở fork — **không cần flag
khi start**, vì API Android không cho app khác ghi command-line của browser.

> ⚠ Chrome/WebView chính thức KHÔNG làm được (DevTools chỉ qua Unix socket+adb).
> Đây là lý do phải tự build fork và patch mã nguồn.

Vị trí mã thay đổi theo từng release Chromium — cách làm đúng là
**search trong tree đã checkout**, không sao chép theo đường dẫn cũ.

---

## Bước 1 — Tìm nơi quyết định địa chỉ/bind DevTools HTTP

Trong `src/` (tree đã checkout):

```bash
grep -rn "remote-debugging-port" content/browser/ chrome/browser/ | grep -i "tcp\|listen\|port" | head -40
grep -rn "kRemoteDebuggingPort" content/ chrome/ | grep -i tcp | head
grep -rn "Create.*DevToolsHttpHandler\|devtools_http_handler" content/browser/ | head
```

Ở hầu hết Chromium hiện đại, điểm chính là
`content/browser/devtools/devtools_http_handler.cc`.

Tìm đoạn build `net::HostPortPair` cho HTTP server:

```bash
grep -n "HostPortPair" content/browser/devtools/devtools_http_handler.cc
sed -n '130,200p' content/browser/devtools/devtools_http_handler.cc
```

Thông thường có logic kiểu:

```cc
int port = GetWebSocketPort(command_line, "remote-debugging-switches",
                            net::GetDefaultPort("http"));
...
auto host_port = net::HostPortPair(host, port);
```

## Bước 2 — Patch: Android luôn bind `127.0.0.1:9222`

Chèn gần nơi tạo server (ngay trước khi `DevToolsHttpHandlerFactory`/`Start()`):

```cc
#if BUILDFLAG(IS_ANDROID)
  // ToolTX fork: luôn bật Remote Debugging loopback, không phụ thuộc command line.
  std::string tx_loopback = "127.0.0.1:9222";
  host = net::IPAddress::FromIPLiteral? /* không cần —— dùng fixed pair */;
  auto host_port = net::HostPortPair("127.0.0.1", 9222);
#else
  auto host_port = ...(như gốc)...
#endif
```

Tức là **gộp thẳng HostPortPair cố định** vào nhánh Android, bỏ qua hoàn toàn
kết quả parse `remote-debugging-port` flag. Nhớ đưa nó vào scope đủ lớn để
biến `host_port` được dùng khi `Start()`.

Tiếp theo giữ cho server không yêu cầu "authenticated connections" khi
không có DevTools `--remote-allow-origins`... (bản thường, DevTools HTTP
trong build không debuggable sẽ ko khởi động — đây chính là chỗ patch
xử lý). Ở một số bản có điều kiện:

```cc
bool enabled = command_line->HasSwitch("remote-debugging-port") ||
               IsiOS() /* hoặc */ IsAndroid() && IsDebuggable();
```

→ đổi thành `true` khi `BUILDFLAG(IS_ANDROID)`.

## Bước 3 — Giữ CDP sống khi browser ra nền

Android có thể ngắt tiến trình nền. Giữ kết nối + đừng để Doze tắt
network quá sớm, trong `chrome/android/java/.../ChromeBackgroundServiceManager`
hoặc đơn giản nhất: ở bước runtime, bật "giữ màn hình sáng" trong ToolTX
(hcdp/`start_browser` + `FLAG_KEEP_SCREEN_ON`). Không cần sửa thêm mã fork.

## Bước 4 — Sau patch

```bash
autoninja -C out/release chrome_apk
# ra out/release/apks/ChromePublic.apk, ký, cài: adb install -r
```

**Không cần**: `--remote-debugging-port`, debuggable build, ADB lúc dùng,
root. Runtime chỉ cần: ToolTX APK mở fork bằng `startActivity` + đọc
`127.0.0.1:9222`.

---

## Gợi ý xác minh trước khi đóng gói

Với desktop Chromium (máy build) chạy với `--remote-debugging-port=9222`
để test luồng hcdp:

```bash
npx -y @puppeteer/browsers
# hoặc dùng trình duyệt thường:
google-chrome --headless --remote-debugging-port=9222 about:blank &
curl -s http://127.0.0.1:9222/json/version
```

Trên Android đã cài fork: mở fork tay → trong ToolTX bấm START BROWSER
→ hcdp đọc `/json/version` → tab game Sunwin hiện ra (đăng nhập bằng tay
lần đầu, login lưu trong profile fork).
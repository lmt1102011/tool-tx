#!/usr/bin/env bash
# build.sh — Build Chromium fork có DevTools TCP 127.0.0.1:9222 LUÔN BẬT
# cho ToolTX: chạy hoàn toàn trên điện thoại, không PC/ADB/server lúc dùng.
#
# MÔI TRƯỜNG BẮT BUỘC: Linux (hoặc WSL2 trên Windows). KHÔNG build được trên phone.
# Yêu cầu: ~16GB+ RAM, 30-90GB đĩa, git/curl/unzip, python3.
#
# Chỉ chạy MỘT LẦN trên máy build. Sau đó cài APK vào điện thoại,
# app ToolTX sẽ mở fork và bắt CDP 127.0.0.1:9222 bằng hcdp.py.

set -euo pipefail
cd "$(dirname "$0")"
SRC=~/chromium-src

echo "==> [1/6] Depot tools"
if [ ! -d ~/depot_tools ]; then
  git clone https://chromium.googlesource.com/chromium/tools/depot_tools.git ~/depot_tools
fi
export PATH="$HOME/depot_tools:$PATH"

echo "==> [2/6] Checkout Chromium (android hooks)"
if [ ! -d "$SRC/src/.git" ]; then
  mkdir -p "$SRC"
  cd "$SRC"
  fetch --nohooks android
fi
cd "$SRC/src"
gclient runhooks

echo "==> [3/6] Dependencies Android"
sudo ./build/install-build-deps-android.sh 2>/dev/null || true

echo "==> [4/6] GN args"
mkdir -p out/release
cat > out/release/args.gn <<'EOF'
target_os = "android"
target_cpu = "arm64"
is_debug = false
is_official_build = false
symbol_level = 0
android_channel = "dev"
enable_kotlin = true
EOF
gn gen out/release

echo "==> [5/6] ÁP DỤNG PATCH CDP ALWAYS-ON (xem PATCH.md)"
if [ -f ../PATCH.txdiff ]; then
  patch -p1 < ../PATCH.txdiff || echo "!! patch thủ công theo PATCH.md"
elif [ -f ../../fork/PATCH.txdiff ]; then
  patch -p1 < ../../fork/PATCH.txdiff || echo "!! patch thủ công theo PATCH.md"
else
  echo "!! tạo PATCH.txdiff (hoặc sửa tay) THEO HƯỚNG DẪN PATCH.md trước."
  exit 1
fi

echo "==> [6/6] Build chrome_apk (chờ 1-2h máy mạnh, 3-6h máy yếu)"
autoninja -C out/release chrome_apk

echo ""
echo "APK: $SRC/src/out/release/apks/ChromePublic.apk"
echo "Ký (debug key):"
APKSIGNER="$HOME/Android/Sdk/build-tools/$(ls ~/Android/Sdk/build-tools | tail -1)/apksigner"
if [ -x "$APKSIGNER" ]; then
  keytool -genkeypair -v -keystore ~/.android/avd/release-fork.keystore \
    -alias fork -keyalg RSA -keysize 2048 -validity 10000 \
    -storepass tooltx2026 -keypass tooltx2026 -dname "CN=ToolTX Fork" 2>/dev/null || true
  "$APKSIGNER" sign --ks ~/.android/avd/release-fork.keystore \
    --ks-pass pass:tooltx2026 --key-pass pass:tooltx2026 \
    --out out/release/ChromiumFork-signed.apk out/release/apks/ChromePublic.apk
  echo "Install: adb install -r out/release/ChromiumFork-signed.apk"
else
  echo "Cài apksigner (build-tools của Android SDK) rồi ký thủ công."
fi
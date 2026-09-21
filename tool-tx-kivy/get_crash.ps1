# get_crash.ps1 — Lấy crash log từ điện thoại Android về PC
# Cách dùng: powershell -ExecutionPolicy Bypass -File get_crash.ps1
#
# Yêu cầu: ADB đã cài và điện thoại đã bật USB Debugging.
# Kết nối USB → chạy script → file crash.log sẽ lưu về thư mục hiện tại.

$ErrorActionPreference = "Stop"

# Kiểm tra adb
$adb = Get-Command adb -ErrorAction SilentlyContinue
if (-not $adb) {
    Write-Host "LOI: adb khong tim thay. Cai ADB thuong: https://developer.android.com/tools/adb" -ForegroundColor Red
    Write-Host "  Hoac chay: winget install Google.PlatformTools" -ForegroundColor Yellow
    exit 1
}

# Kiểm tra thiết bị
$devices = & adb devices 2>&1 | Select-String -Pattern "device$"
if (-not $devices) {
    Write-Host "LOI: Khong tim thay thiet bi. Ket noi USB va bat USB Debugging." -ForegroundColor Red
    exit 1
}

Write-Host "Tim thay thiet bi: " -NoNewline
Write-Host ($devices | Select-Object -First 1) -ForegroundColor Green

# Pull crash log từ /sdcard/Download/
$remotePath = "/sdcard/Download/crash.log"
$localPath = ".\crash.log"

Write-Host "Dang pull crash log tu $remotePath ..."
$result = & adb pull $remotePath $localPath 2>&1

if ($LASTEXITCODE -eq 0 -and (Test-Path $localPath)) {
    $size = (Get-Item $localPath).Length
    Write-Host "OK! Da lay crash log ve: $localPath ($size bytes)" -ForegroundColor Green
    Write-Host ""
    Write-Host "--- NOI DUNG CRASH LOG ---" -ForegroundColor Cyan
    Get-Content $localPath -Encoding UTF8
    Write-Host "--- END ---" -ForegroundColor Cyan
} else {
    Write-Host "LOI: Khong lay duoc crash log." -ForegroundColor Red
    Write-Host "  Kiem tra: file crash.log co ton tai tren dien thoai khong?" -ForegroundColor Yellow
    Write-Host "  Thu: adb shell ls -la /sdcard/Download/crash.log" -ForegroundColor Yellow
}

# Cũng pull fault.log nếu có
$faultRemote = "/sdcard/Download/fault.log"
$faultLocal = ".\fault.log"
$result2 = & adb pull $faultRemote $faultLocal 2>&1
if ($LASTEXITCODE -eq 0 -and (Test-Path $faultLocal)) {
    $size2 = (Get-Item $faultLocal).Length
    Write-Host ""
    Write-Host "Da lay fault.log: $faultLocal ($size2 bytes)" -ForegroundColor Green
    Write-Host "--- FAULT LOG ---" -ForegroundColor Cyan
    Get-Content $faultLocal -Encoding UTF8
    Write-Host "--- END ---" -ForegroundColor Cyan
}

# Also pull from app internal dir
$appDir = "/data/data/org.lmt1102011.tooltx/files/crash.log"
$localApp = ".\crash_internal.log"
$result3 = & adb pull $appDir $localApp 2>&1
if ($LASTEXITCODE -eq 0 -and (Test-Path $localApp)) {
    $size3 = (Get-Item $localApp).Length
    Write-Host ""
    Write-Host "Da lay crash.log (internal): $localApp ($size3 bytes)" -ForegroundColor Green
    Write-Host "--- INTERNAL CRASH LOG ---" -ForegroundColor Cyan
    Get-Content $localApp -Encoding UTF8
    Write-Host "--- END ---" -ForegroundColor Cyan
}

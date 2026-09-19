@echo off
setlocal
cd /d "%~dp0"
echo ============================================
echo  TX TOOL - AGENT CHROME (chay tai may ban)
echo ============================================

where node >nul 2>nul
if errorlevel 1 (
  echo KHONG TIM THAY NODE.JS. Cai tu https://nodejs.org (phien ban 22+) roi chay lai.
  pause
  exit /b 1
)

if not exist "agent_chrome.js" (
  echo Tai agent_chrome.js...
  where curl.exe >nul 2>nul
  if errorlevel 1 (
    echo Can curl.exe hoac chep san file agent_chrome.js vao cung thu muc.
    pause
    exit /b 1
  )
  curl.exe -L -o "agent_chrome.js" "%~2agent_chrome.js"
  if errorlevel 1 (
    echo Tai khong duoc agent_chrome.js. Kiem tra URL server trong lenh.
    pause
    exit /b 1
  )
)

set "CODE=%~1"
set "SRV=%~2"
if "%CODE%"=="" set /p CODE=Nhap MA LIEN KET (6 ky tu): 
if "%SRV%"=="" set /p SRV=URL SERVER: 

if "%CODE%"=="" set CODE=______
if "%SRV%"=="" set SRV=http://localhost:8787

echo .
echo Dang mo Chrome tai may ban va noi server...
echo Giu cua so nay mo. Ctrl+C de dung.
echo .
node "agent_chrome.js" --server "%SRV%" --code "%CODE%"

echo .
echo Agent da dung.
pause
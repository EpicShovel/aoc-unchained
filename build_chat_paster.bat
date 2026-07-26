@echo off
rem Build AoC Chat Color Paster to a standalone Windows executable.
rem AV-friendly settings: onedir layout, UPX off, custom icon, version
rem resource, and an optional Authenticode signature (skipped silently if
rem signtool or the EpicShovel cert is not available).
rem Run this from the aoc-unchained folder.

cd /d "%~dp0"

set PY=python
if defined PYTHON (set PY=%PYTHON%)

set DOTNET_ROLL_FORWARD=Major

rem 1. Generate the app icon (needs Pillow at build time only).
%PY% make_icon.py
if errorlevel 1 (
  echo Icon generation failed.
  exit /b 1
)

rem 2. Build.
%PY% -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name "AoC Chat Color Paster" ^
  --icon chat_color.ico ^
  --version-file version_info.txt ^
  --upx-dir "" ^
  --distpath "dist" ^
  --workpath "build" ^
  aoc_chat_color_paster.py

if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

rem 3. Optional: sign the exe (self-signed EpicShovel/Requiem Nex cert,
rem    thumbprint from proje\Combat Monitor\CombatMonitor_py\sign_config.ps1).
rem    Uses PowerShell's Set-AuthenticodeSignature - no Windows SDK needed.
set THUMBPRINT=7041AEF6E91BBAC815A7977FE7097FD42A453048
powershell -NoProfile -Command "$c = Get-Item Cert:\CurrentUser\My\%THUMBPRINT% -ErrorAction SilentlyContinue; if (-not $c) { echo 'Signing cert not found - exe left unsigned.'; exit 0 }; try { Set-AuthenticodeSignature -FilePath 'dist\AoC Chat Color Paster\AoC Chat Color Paster.exe' -Certificate $c -HashAlgorithm SHA256 -TimestampServer 'http://timestamp.digicert.com' | Out-Null; echo 'Exe signed.' } catch { echo 'Signing failed - exe left unsigned.' }"
echo.
echo Build complete: dist\AoC Chat Color Paster\AoC Chat Color Paster.exe

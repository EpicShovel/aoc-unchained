@echo off
rem Build AoC Chat Color Paster to a standalone Windows executable.
rem Uses PyInstaller with the safer onedir layout (lower AV false-positive rate than onefile).
rem Run this from the aoc-unchained folder.

cd /d "%~dp0"

set PY=python
if defined PYTHON (set PY=%PYTHON%)

set DOTNET_ROLL_FORWARD=Major

%PY% -m PyInstaller ^
  --noconfirm ^
  --onedir ^
  --windowed ^
  --name "AoC Chat Color Paster" ^
  --upx-dir "" ^
  --distpath "dist" ^
  --workpath "build" ^
  aoc_chat_color_paster.py

if errorlevel 1 (
  echo Build failed.
  exit /b 1
)

echo.
echo Build complete: dist\AoC Chat Color Paster\AoC Chat Color Paster.exe

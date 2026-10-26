@echo off
title AutoKetik Launcher
cd /d "%~dp0"

:: 1. Periksa apakah Python terpasang di sistem
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo ============================================================
    echo  [ERROR] Python tidak terdeteksi di PATH sistem!
    echo  Pastikan Python sudah terinstal di komputer Anda.
    echo ============================================================
    pause
    exit /b 1
)

:: 2. Jalankan AutoKetikGUI dengan pythonw (tanpa jendela hitam terminal)
start "" pythonw AutoKetikGUI.py

:: 3. Jika pythonw gagal, coba fallback ke python biasa
if %errorlevel% neq 0 (
    python AutoKetikGUI.py
    if %errorlevel% neq 0 (
        echo.
        echo ============================================================
        echo  [ERROR] Gagal membuka AutoKetikGUI.
        echo  Pastikan dependensi sudah terinstal dengan menjalankan:
        echo  pip install -r requirements.txt
        echo ============================================================
        pause
    )
)

exit

@echo off
:: Launcher bota Kosa - automatycznie uruchamia jako Administrator
:: Kliknij dwukrotnie zeby uruchomic bota z podgladem debug

cd /d "%~dp0"

:: Sprawdz uprawnienia admina
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Potrzebne uprawnienia administratora - podnoszenie...
    powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c cd /d \"%~dp0\" && .\venv\Scripts\python.exe -m src.bot --debug && pause'"
    exit /b
)

echo Uruchamiam Kosa Bot jako Administrator...
.\venv\Scripts\python.exe -m src.bot --debug
pause

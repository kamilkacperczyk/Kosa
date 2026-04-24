@echo off
:: Launcher bota BeSafeFish - automatycznie uruchamia jako Administrator
:: Kliknij dwukrotnie zeby uruchomic bota z podgladem debug
:: Uzywa run.py ktory pozwala wybrac tryb/wariant bota (versions/<tryb>/<wariant>/)

cd /d "%~dp0"

:: Sprawdz uprawnienia admina
net session >nul 2>&1
if %errorLevel% neq 0 (
    echo Potrzebne uprawnienia administratora - podnoszenie...
    powershell -Command "Start-Process cmd -Verb RunAs -ArgumentList '/c cd /d \"%~dp0\" && py run.py --debug && pause'"
    exit /b
)

echo Uruchamiam BeSafeFish Bot jako Administrator...
py run.py --debug
pause

@echo off
cd /d "%~dp0"
"C:\Users\REDACTED-USER-PATH\Desktop\Repos\Kosa\.venv\Scripts\python.exe" besafefish.py
if errorlevel 1 pause

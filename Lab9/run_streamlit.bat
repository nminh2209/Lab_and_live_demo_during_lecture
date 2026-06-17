@echo off
cd /d "%~dp0"
set PYTHONPATH=src
".venv\Scripts\streamlit.exe" run src\streamlit_app.py
pause

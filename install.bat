@echo off
REM Installer for ReadingRabbit on Windows 10
python -m venv venv
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

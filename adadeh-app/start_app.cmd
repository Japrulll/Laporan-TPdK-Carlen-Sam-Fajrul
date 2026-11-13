@echo off
setlocal
cd /d "%~dp0"
if not defined ADADEH_PYTHON set "ADADEH_PYTHON=%USERPROFILE%\.venvs\adadeh\Scripts\python.exe"
if not exist "%ADADEH_PYTHON%" (
  echo Lingkungan Python belum tersedia. Ikuti instalasi pada README.md.
  exit /b 1
)
"%ADADEH_PYTHON%" -m streamlit run "%~dp0streamlit_app.py" --server.address 127.0.0.1 --server.port 8501 --server.headless true

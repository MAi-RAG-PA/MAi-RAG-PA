@echo off
cd /d "%~dp0"
echo Starting MAi-RAG-PA...

:: Activate venv
call venv\Scripts\activate.bat

:: Start Ollama (if installed)
where ollama >nul 2>nul
if %errorlevel%==0 (
    curl -s http://localhost:11434/api/tags >nul 2>nul
    if errorlevel 1 start /B ollama serve
)

:: Start Qdrant
if exist qdrant.exe (
    curl -s http://localhost:6333/dashboard >nul 2>nul
    if errorlevel 1 start /B qdrant.exe
)

:: Open Browser
start http://localhost:8000

:: Start Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000

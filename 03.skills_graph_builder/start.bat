@echo off
REM Skills Graph Case Study - Windows Startup Script

echo 🚀 Starting Skills Graph Case Study...

REM Check if virtual environment exists
if not exist ".venv" (
    echo 📦 Creating virtual environment...
    python -m venv .venv
)

REM Activate virtual environment
echo 🔧 Activating virtual environment...
call .venv\Scripts\activate.bat

REM Install dependencies
echo 📚 Installing dependencies...
pip install -r requirements.txt

REM Check for API key
if not exist ".env" (
    echo ⚠️  No .env file found. Creating from template...
    copy .env.example .env
    echo 🔑 Please edit .env and add your OpenAI API key:
    echo    OPENAI_API_KEY=sk-proj-your-key-here
    echo.
    echo Press any key when ready to continue...
    pause >nul
)

REM Generate synthetic data if it doesn't exist
if not exist "data\samples\people.jsonl" (
    echo 📊 Generating synthetic data...
    python scripts\generate_synth_data.py
)

REM Load environment variables
if exist ".env" (
    for /f "usebackq tokens=1,2 delims==" %%a in (".env") do (
        if not "%%a"=="" if not "%%a:~0,1%"=="#" (
            set "%%a=%%b"
        )
    )
)

REM Start the application
echo 🌐 Starting application...
echo.
echo Backend API will run on: http://localhost:8000
echo Streamlit UI will run on: http://localhost:8501
echo.
echo Press Ctrl+C to stop both services
echo.

REM Start backend
echo 🔧 Starting backend API...
set PYTHONPATH=%CD%
start /B python -m uvicorn src.app:app --host 0.0.0.0 --port 8000

REM Wait a moment
timeout /t 3 /nobreak >nul

REM Start Streamlit
echo 🎨 Starting Streamlit UI...
start /B streamlit run ui\streamlit_app.py

echo ✅ Both services started! Check your browser.
echo Press any key to stop services...
pause >nul

REM Cleanup
echo 🛑 Stopping services...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM streamlit.exe 2>nul

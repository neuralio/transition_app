@echo off
REM Start TRANSITION Frontend (Next.js) - Windows

echo 🎨 Starting TRANSITION Frontend...
echo.

REM Navigate to frontend directory
cd frontend

REM Check if node_modules exists
if not exist "node_modules\" (
    echo ❌ node_modules not found!
    echo Please install dependencies first: npm install
    exit /b 1
)

REM Start the development server
echo ✅ Starting Next.js development server on http://localhost:3000
echo.
echo Available pages:
echo   - http://localhost:3000       (Home page)
echo   - http://localhost:3000/chat  (Chat interface)
echo.
echo Press Ctrl+C to stop the server
echo.

npm run dev

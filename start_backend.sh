#!/bin/bash
# Start TRANSITION Backend API Server
# Note: Make sure you've activated your virtual environment before running this!

echo "🚀 Starting TRANSITION Backend API..."
echo ""

# Check if uvicorn is installed (assumes you're already in a virtual env)
if ! python -c "import uvicorn" 2>/dev/null; then
    echo "❌ uvicorn not installed!"
    echo "Please install dependencies: pip install -r requirements.txt"
    exit 1
fi

# Start the server
echo "✅ Starting server on http://localhost:8000 (with auto-reload)"
echo ""
echo "API Endpoints:"
echo "  - http://localhost:8000              (Health check)"
echo "  - http://localhost:8000/docs         (Swagger UI)"
echo "  - http://localhost:8000/api/query    (Chat endpoint)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Use uvicorn directly with reload (proper way)
uvicorn backend.api.server:app --host 0.0.0.0 --port 8000 --reload

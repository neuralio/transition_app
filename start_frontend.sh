#!/bin/bash
# Start TRANSITION Frontend (Next.js)

echo "🎨 Starting TRANSITION Frontend..."
echo ""

# Navigate to frontend directory
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "❌ node_modules not found!"
    echo "Please install dependencies first: npm install"
    exit 1
fi

# Start the development server
echo "✅ Starting Next.js development server on http://localhost:3000"
echo ""
echo "Available pages:"
echo "  - http://localhost:3000       (Home page)"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

npm run dev

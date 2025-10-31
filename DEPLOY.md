# TRANSITION Deployment Guide

## Prerequisites
- Python 3.12+
- Node.js 20+
- `uv` package manager: https://github.com/astral-sh/uv

## Setup Commands

```bash
# 1. Clone repository
git clone <repo-url>
cd Transition

# 2. Python setup with uv
uv venv esa
source esa/bin/activate  # Linux/macOS
# esa\Scripts\activate   # Windows
uv pip sync requirements.txt

# 3. Frontend setup
cd frontend
npm install
cd ..

# 4. Configure environment variables
# Copy template and add your OpenAI API key
cp .env.example .env
nano .env  # Edit and replace 'your_openai_api_key_here' with your actual key
# Get your key from: https://platform.openai.com/api-keys
```

## Running the Application

**Open 2 terminals:**

**Terminal 1 - Backend:**
```bash
source esa/bin/activate
python backend/api/server.py
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

**Access:** http://localhost:3000

## Quick Test

```bash
# In new terminal (with esa activated)
source esa/bin/activate
python use_cases/mlu/run_mlu.py --query mlu_04 --parcels 10 --scenario moderate
```

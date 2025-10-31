# TRANSITION Platform
## EO-Informed Agent-Based Models for Digital Twins Applications

**Version:** 1.0.0
**Status:** Active Development
**License:** MIT

---

## 🌍 Overview

TRANSITION is a climate-resilience platform that creates spatial digital twins to support sustainable resource management. Built on **Multi-Level Agent-Based Modeling (ML-ABM)**, the platform integrates **real Earth Observation (EO) data** with advanced AI/ML to provide actionable insights for climate adaptation.

### Key Features

- **Multi-Level ABM**: 4-level agent architecture (Individual, Community, Market, Policy)
- **Real EO Data**: 100% real satellite data (Sentinel, Landsat, MODIS) - NO dummy data
- **Chat Interface**: ✅ Natural language queries via web chat (frontend ↔ backend integration)
- **PECS Framework**: Cognitive architecture for realistic agent decision-making
- **Reinforcement Learning**: Hybrid decision-making with Gymnasium/Stable-Baselines3 PPO
- **Plugin Scenarios**: Modular system (CCA, GCP, MLU + extensions)
- **FastAPI Backend**: Production-ready REST API for digital twin orchestration

---

## 🏗️ Architecture

### Backend First, Frontend Last

**Development Priority:**
1. ✅ Backend (FastAPI, Mesa ML-ABM, RL, EO Data) 
2. Frontend (Next.js, React, Visualization) 

### Tech Stack

#### Backend
- **ABM**: Mesa 3.3+
- **RL**: Gymnasium 0.29+, Stable-Baselines3 2.2+ (PPO)
- **ML/AI**: PyTorch 2.x, scikit-learn
- **Geospatial**: Rasterio 1.3+, xarray 2023.x+, GeoPandas 0.14+
- **API**: FastAPI 0.104+, Uvicorn, Pydantic 2.5+
- **Database**: PostgreSQL 15/PostGIS, TimescaleDB, MongoDB, Redis

#### Frontend ✅ SETUP COMPLETE
- Next.js 15, React 18, TypeScript
- Tailwind CSS v4, shadcn/ui
- Dark/Light theme support
- Leaflet.js, Recharts (planned)

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+** (recommended 3.12.3)
- **Node.js 18+** (for frontend - recommended 20+)
- **npm** (comes with Node.js)
- **Git**

Optional (for production):
- PostgreSQL 15 + PostGIS
- Redis 7.x
- Docker Desktop

### Complete Deployment Guide 

Follow these steps to deploy TRANSITION on a new machine:

**🚀 Quick Start (for `uv` users):**
```bash
# 1. Clone
git clone <repo-url> && cd transition_app

# 2. Python setup with uv (fast!)
uv venv esa && source esa/bin/activate
uv pip sync requirements.txt

# 3. Create .env with API key
echo "API_KEY=sk-your-key-here" > .env

# 4. Frontend setup
cd frontend && npm install && cd ..

# 5. Start servers (2 terminals)
# Terminal 1: source esa/bin/activate && python backend/api/server.py
# Terminal 2: cd frontend && npm run dev

# 6. Access: http://localhost:3000
```

**📖 Detailed instructions below:**

#### Prerequisites

1. **Install Python 3.12+**
   ```bash
   # Check Python version
   python --version  # Should be 3.12 or higher
   ```

2. **Install Node.js 20+**
   ```bash
   # Check Node.js version
   node --version  # Should be 20 or higher
   npm --version
   ```

3. **Install Git**
   ```bash
   git --version
   ```

#### Step 1: Clone Repository

```bash
# Clone the repository
git clone <repository-url>
cd Transition
```

#### Step 2: Backend Setup (Python)

**Option A: Using `uv` (Recommended - Fast)**

```bash
# Install uv if not already installed
# See: https://github.com/astral-sh/uv
curl -LsSf https://astral.sh/uv/install.sh | sh  # Linux/macOS
# Or: pip install uv

# Create virtual environment with uv
uv venv esa

# Activate virtual environment
source esa/bin/activate  # Linux/macOS
# esa\Scripts\activate   # Windows PowerShell

# Install dependencies from requirements.txt (this takes ~2 minutes with uv)
uv pip sync requirements.txt

# Verify installation
python -c "import mesa; import torch; print('✅ Python dependencies installed successfully')"
```

**Option B: Using Standard Python (Slower)**

```bash
# Create Python virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows PowerShell

# Install Python dependencies (this may take 5-10 minutes)
pip install --upgrade pip
pip install -r requirements.txt

# Verify installation
python -c "import mesa; import torch; print('✅ Python dependencies installed successfully')"
```

**📌 Note:** This project uses `uv` for faster dependency management. If using standard `pip`, expect longer install times.

#### Step 3: Configure Environment Variables

```bash
# Create .env file (required for the LLM's API)
cat > .env << 'EOF'
# API Key (REQUIRED for LLM interface)
API_KEY=your_api_key_here

# Backend URL (default: http://localhost:8000)
BACKEND_URL=http://localhost:8000

# Edit .env file and add your actual API keys
nano .env  # or use any text editor
```

#### Step 4: Frontend Setup (Node.js)

```bash
# Navigate to frontend directory
cd frontend

# Install Node.js dependencies (this may take 3-5 minutes)
npm install

# Return to project root
cd ..
```

#### Step 5: Start the Application

**Open 2 Terminal Windows:**

**Terminal 1 - Backend Server:**
```bash
# Activate Python environment
source esa/bin/activate  # Linux/macOS (if using uv)
# source venv/bin/activate  # Linux/macOS (if using standard pip)
# esa\Scripts\activate   # Windows (if using uv)
# venv\Scripts\activate   # Windows (if using standard pip)

# Start FastAPI backend (runs on http://localhost:8000)
python backend/api/server.py

# You should see:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

**Terminal 2 - Frontend Server:**
```bash
# Navigate to frontend
cd frontend

# Start Next.js dev server (runs on http://localhost:3000)
npm run dev

# You should see:
# ▲ Next.js 15.x.x
# - Local:        http://localhost:3000
```

#### Step 7: Access the Application

1. **Open browser:** http://localhost:3000
2. **You should see:** TRANSITION chat interface
3. **Test with query:** "Simulate wheat under moderate scenario for 10 years with 20 farmers"

#### Step 8: Verify Installation

**Test Backend (Terminal 1 - keep backend running):**
```bash
# In new terminal window
curl http://localhost:8000/api/health
# Should return: {"status":"healthy"}
```
---

### 🚨 Troubleshooting Common Issues

#### Issue 1: "Module not found" errors
```bash
# Reinstall Python dependencies
pip install --force-reinstall -r requirements.txt
```

#### Issue 2: "API_KEY not found"
```bash
# Check .env file exists and has your key
cat .env | grep API_KEY

# Set temporarily in terminal
export API_KEY='your-key-here'  # Linux/macOS
# $env:API_KEY='your-key-here'  # Windows PowerShell
```

#### Issue 3: Frontend won't start
```bash
# Clear npm cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

#### Issue 4: Port already in use
```bash
# Backend (port 8000)
lsof -ti:8000 | xargs kill -9  # Linux/macOS
# netstat -ano | findstr :8000  # Windows (then kill process)

# Frontend (port 3000)
lsof -ti:3000 | xargs kill -9  # Linux/macOS
```
---

### 📦 Production Deployment

```bash
docker-compose up --build -d
```
---

## 📁 Project Structure

```
transition_app/
│
├── backend/                    # Backend code (Python)
│   ├── api/                   # FastAPI (Dev2 PRIMARY)
│   ├── simulation/            # Mesa ABM (Dev1 PRIMARY)
│   ├── rl/                    # RL (Dev1 PRIMARY)
│   ├── data/                  # EO Data (Dev1 PRIMARY)
│   ├── geospatial/            # Geospatial (Dev1 PRIMARY)
│   ├── db/                    # Database (Dev2 PRIMARY)
│   ├── services/              # SHARED (Integration Layer)
│   └── tests/                 # Both developers
│
├── infrastructure/            # DevOps (Dev2 PRIMARY)
│   ├── docker/
│   ├── kubernetes/
│   └── terraform/
│
└── README.md                  # This file
```
---

## 🐳 Docker Setup 

```bash
# Build and run all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

---

## 📊 Data Philosophy

### Real Data ONLY

- **100% EO-informed data** from Sentinel, CMIP6, ERA5
- **NO dummy/mock/synthetic data** anywhere in the codebase
- **Validation**: RMSE < 15% against historical observations (2000-2020)

### Data Sources

- **Sentinel-1**: SAR imagery (soil moisture)
- **CMIP6**: Climate scenarios (RCP 2.6, 4.5, 6.0, 8.5)
- **ERA5**: Climate reanalysis

---

## 🛠️ Development Tools

### Required

- Python 3.11+
- Git
- PostgreSQL 15 + PostGIS
- Redis 7.x

### Recommended

- VS Code with extensions:
  - Python
  - Pylance
  - Black Formatter
  - Ruff
- Docker Desktop
- QGIS 3.x (for geospatial data visualization)
- Postman/Insomnia (API testing)

---

## 📖 Context7 MCP Integration

**ALWAYS use Context7 MCP for up-to-date library documentation!**

### Two-Step Process

```bash
# 1. Resolve library ID
mcp__context7__resolve-library-id → "mesa"
# Returns: /projectmesa/mesa

# 2. Get documentation
mcp__context7__get-library-docs → {
  "context7CompatibleLibraryID": "/projectmesa/mesa",
  "topic": "agent-based modeling"
}
```

### Key Libraries

- Mesa: `/projectmesa/mesa`
- PyTorch: `/pytorch/pytorch`
- Gymnasium: `/farama-foundation/gymnasium`
- Stable-Baselines3: `/dlr-rm/stable-baselines3`
- Rasterio: `/rasterio/rasterio`
- xarray: `/pydata/xarray`
- FastAPI: `/tiangolo/fastapi`

---

## 🤝 Contributing

### Commit Message Convention

Use **Conventional Commits**:

```
<type>(<scope>): <subject>

Examples:
feat(simulation): Add FarmerAgent with PECS framework
fix(api): Resolve JWT token expiration bug
refactor(rl): Optimize Gymnasium environment reset()
test(simulation): Add unit tests for cross-scale interactions
docs(api): Update API endpoint documentation
```

### Code Style

- **Python**: Black + Ruff
- **Imports**: isort
- **Type Hints**: mypy

```bash
# Format code
black backend/
ruff check backend/ --fix

# Type check
mypy backend/
```
---

### Issues

Create a GitHub issue for:
- Bug reports
- Feature requests
- Documentation improvements

---

## 🙏 Acknowledgments

- **EU Green Deal** - Climate neutrality by 2050
- **ESA DestinE Initiative** - Digital twin infrastructure
- **Mesa Community** - Agent-based modeling framework
- **Copernicus Programme** - Earth Observation data

---

**Built with ❤️ by the TRANSITION Team**

**Version:** 1.0.0
**Last Updated:** October 2025
**Status:** Active Development

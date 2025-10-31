# TRANSITION Developer Setup Guide

Complete setup instructions for developers joining the TRANSITION project.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

### Required Software
- **Python 3.12+** (recommended 3.12.3)
- **Node.js 18+** (recommended 20+ for Next.js 15)
- **npm** (comes with Node.js)
- **Git**

### Check Your Versions
```bash
python --version    # Should show Python 3.12+
node --version      # Should show v18+
npm --version       # Should show 9+
git --version
```

---

## 🚀 Quick Start (Full Setup)

### 1. Clone the Repository

```bash
git clone <repository-url>
cd Transition
```

### 2. Backend Setup (Python)

#### Create Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

#### Install Python Dependencies
```bash
pip install -r requirements.txt
```

**What gets installed:**
- **ABM Framework**: Mesa 3.3.0+
- **ML/RL**: PyTorch, TensorFlow, Gymnasium, Stable-Baselines3
- **EO Data**: xarray, rasterio, netCDF4
- **Geospatial**: GeoPandas, Shapely, Fiona
- **Web**: FastAPI, Uvicorn, Pydantic
- **Visualization**: Matplotlib, Plotly, Seaborn
- **Testing**: pytest, pytest-cov

#### Verify Backend Installation
```bash
# Test MLU simulation
python use_cases/mlu/run_mlu.py --query mlu_04 --parcels 10 --scenario moderate

# Test CCA simulation
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario moderate --farmers 20
```

### 3. Frontend Setup (Node.js/Next.js)

#### Navigate to Frontend Directory
```bash
cd frontend
```

#### Install Node.js Dependencies
```bash
npm install
```

**What gets installed:**
- **Framework**: Next.js 15, React 18
- **Language**: TypeScript
- **Styling**: Tailwind CSS v4
- **UI Library**: shadcn/ui components
- **Theme**: next-themes (dark/light mode)
- **Icons**: Lucide React
- **Utilities**: clsx, tailwind-merge, class-variance-authority

#### Verify Frontend Installation
```bash
# Start development server
npm run dev

# In another terminal, check if it's running:
curl http://localhost:3000
```

Visit **http://localhost:3000** in your browser. You should see the TRANSITION landing page with a working theme toggle.

#### Build Frontend (Optional - to verify everything works)
```bash
npm run build
```

---

## 📂 Project Structure

```
Transition/
├── backend/                    # Python backend (simulation core)
│   ├── data/                  # Data loaders
│   ├── simulation/            # ABM simulation engine
│   └── api/                   # FastAPI endpoints (planned)
├── frontend/                   # Next.js frontend (NEW)
│   ├── app/                   # Next.js App Router pages
│   ├── components/            # React components
│   ├── lib/                   # Utilities
│   ├── hooks/                 # Custom React hooks
│   └── package.json           # Node.js dependencies
├── use_cases/                  # Use case implementations
│   ├── mlu/                   # Multi-Land Use
│   ├── cca/                   # Climate Change Adaptation
│   └── gcp/                   # Green Credit Policy (planned)
├── llm_interface/              # Natural language interface
├── infrastructure/             # Deployment configs
├── requirements.txt            # Python dependencies
├── .gitignore                 # Git ignore rules
└── README.md                  # Project overview
```

---

## 🔧 Development Workflow

### Backend Development

#### Running Simulations

**Multi-Land Use (MLU):**
```bash
# Basic MLU simulation
python use_cases/mlu/run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario moderate

# With custom multi-level agents
python use_cases/mlu/run_mlu.py --query mlu_05 --years 10 --parcels 15 --scenario moderate \
  --collectives 5 --markets 2 --policies 3

# Ensemble mode (MLU-08)
python use_cases/mlu/run_mlu.py --query mlu_08 --scenario moderate --ensemble-size 30
```

**Climate Change Adaptation (CCA):**
```bash
# Crop yield simulation
python use_cases/cca/run_cca.py --query cca_03 --crop WHEAT --scenario moderate --farmers 20

# PV suitability evaluation
python use_cases/cca/run_cca.py --query cca_04 --scenario moderate --farmers 20

# Cross-scale interactions
python use_cases/cca/run_cca.py --query cca_10 --scenario moderate --farmers 20 \
  --collectives 4 --markets 2 --policies 1
```

**LLM Interface (Natural Language):**
```bash
# Use natural language queries
python llm_interface/transition_agent.py "Simulate wheat under moderate scenario for 10 years with 20 farmers"
python llm_interface/transition_agent.py "Show future climate scenarios for wheat under pessimistic scenario with ensemble size 10"
```

#### Running Backend API (Planned)
```bash
# When FastAPI integration is complete:
uvicorn backend.api.main:app --reload --port 8000
```

### Frontend Development

#### Start Development Server
```bash
cd frontend
npm run dev
```

Server runs at **http://localhost:3000** with hot reload enabled.

#### Adding shadcn/ui Components
```bash
# Add individual components
npx shadcn@latest add card
npx shadcn@latest add dialog
npx shadcn@latest add input
npx shadcn@latest add select

# Add multiple components
npx shadcn@latest add card dialog dropdown-menu table
```

Browse all components: https://ui.shadcn.com/docs/components

#### Building for Production
```bash
npm run build    # Creates optimized production build
npm start        # Runs production server
```

---

## 📦 What's Committed to Git?

### ✅ Committed (Source Code)
- All `.py` files (Python source)
- All `.ts`, `.tsx` files (TypeScript source)
- `package.json` (Node.js dependencies list)
- `requirements.txt` (Python dependencies list)
- Configuration files (`.yaml`, `.json`)
- Documentation (`.md` files)
- Small example data files

### ❌ NOT Committed (Generated/Large Files)
- `node_modules/` (Node.js packages - **~350MB**)
- `.next/` (Next.js build output)
- `__pycache__/` (Python cache)
- `venv/` (Python virtual environment)
- Large EO data files (`.nc`, `.tif`, `.hdf5`)
- Build outputs, logs, temp files
- `package-lock.json` (optional - currently NOT committed)

**Why `package-lock.json` is not committed:**
- Reduces merge conflicts
- Allows flexible dependency resolution
- Developers run `npm install` to generate their own

**If you want to commit lock files:**
Uncomment line 310-312 in `.gitignore`:
```bash
# package-lock.json
# yarn.lock
# pnpm-lock.yaml
```

---

## 🧪 Testing

### Backend Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_landuse_model.py

# Run with coverage
pytest --cov=backend --cov-report=html
```

### Frontend Testing (To Be Set Up)
```bash
cd frontend
npm test         # When Jest/Testing Library is configured
npm run test:e2e # When Playwright/Cypress is configured
```

---

## 🐛 Common Issues & Solutions

### Issue 1: Python Module Not Found
```bash
# Error: ModuleNotFoundError: No module named 'mesa'

# Solution: Make sure virtual environment is activated
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Then reinstall dependencies
pip install -r requirements.txt
```

### Issue 2: Node Modules Missing
```bash
# Error: Cannot find module 'next'

# Solution: Install frontend dependencies
cd frontend
npm install
```

### Issue 3: Port Already in Use
```bash
# Error: Port 3000 is already in use

# Solution 1: Kill the process using port 3000
# Linux/macOS:
lsof -ti:3000 | xargs kill -9

# Windows:
netstat -ano | findstr :3000
taskkill /PID <PID> /F

# Solution 2: Use a different port
PORT=3001 npm run dev
```

### Issue 4: Build Fails with TypeScript Errors
```bash
# Error: Type errors in build

# Solution: Check for type issues
npm run lint
npx tsc --noEmit  # Type check without building
```

### Issue 5: Theme Not Working (Frontend)
```bash
# Symptom: Dark mode toggle doesn't work

# Check: Ensure suppressHydrationWarning is on <html> tag
# File: frontend/app/layout.tsx
# Should have: <html lang="en" suppressHydrationWarning>
```

### Issue 6: Missing EO Data
```bash
# Error: FileNotFoundError: data/LUSA_MAIZE_RCP45_2050.nc

# Solution: The large EO data files are NOT in Git
# Contact project lead for access to data storage
# Data location: /home/ggous/Downloads/PILOT_THESSALONIKI_DATA
```

---

## 🔐 Environment Variables

### Backend (.env)
Create `.env` file in project root (NOT committed to Git):

```bash
# API Keys (if needed)
OPENAI_API_KEY=your_key_here

# Database (if using)
DATABASE_URL=postgresql://user:password@localhost:5432/transition

# Paths
DATA_PATH=/path/to/eo/data
```

### Frontend (.env.local)
Create `.env.local` in `frontend/` folder:

```bash
# API endpoint
NEXT_PUBLIC_API_URL=http://localhost:8000

# Feature flags
NEXT_PUBLIC_ENABLE_MAPS=true
```

---

## 📚 Documentation References

### Project Documentation
- [CLAUDE.md](CLAUDE.md) - Project context, coding standards, architecture
- [PRD.md](PRD.md) - Product requirements, use cases, stakeholders
- [PLANNING.md](PLANNING.md) - Tech stack, infrastructure, deployment
- [ARCHITECTURE.md](ARCHITECTURE.md) - PECS framework, multi-level ABM
- [MULTILEVEL-GUIDE.md](MULTILEVEL-GUIDE.md) - Multi-level ABM configuration

### Use Case Documentation
- [use_cases/mlu/USER_STORIES.md](use_cases/mlu/USER_STORIES.md) - MLU user stories
- [use_cases/mlu/EXAMPLE_CASES_PROMPTS.md](use_cases/mlu/EXAMPLE_CASES_PROMPTS.md) - MLU CLI examples
- [use_cases/cca/USER_STORIES.md](use_cases/cca/USER_STORIES.md) - CCA user stories
- [use_cases/cca/EXAMPLE_CASES_PROMPTS.md](use_cases/cca/EXAMPLE_CASES_PROMPTS.md) - CCA CLI examples

### Frontend Documentation
- [frontend/SETUP.md](frontend/SETUP.md) - Comprehensive frontend guide
- [FRONTEND_QUICKSTART.md](FRONTEND_QUICKSTART.md) - Quick start reference

### External Documentation
- **Mesa**: Use Context7 MCP tool for latest docs
- **Next.js**: https://nextjs.org/docs
- **shadcn/ui**: https://ui.shadcn.com
- **Gymnasium**: https://gymnasium.farama.org
- **FastAPI**: https://fastapi.tiangolo.com

---

## 🤝 Team Collaboration

### Before You Start Coding
1. **Pull latest changes**: `git pull origin main`
2. **Check current branch**: `git branch`
3. **Create feature branch**: `git checkout -b feature/your-feature-name`

### Making Changes
1. **Backend**: Activate virtual environment first
2. **Frontend**: Navigate to `frontend/` folder
3. **Test locally** before committing
4. **Follow code standards** in [CLAUDE.md](CLAUDE.md)

### Committing Changes
```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "Add: Brief description of what you added"

# Push to remote
git push origin feature/your-feature-name
```

### Pull Request Guidelines
- Descriptive title and description
- Reference related issues
- Include screenshots for UI changes
- Ensure all tests pass

---

## 🎯 Next Steps After Setup

1. **Explore the codebase**:
   - Run MLU and CCA simulations
   - Check output visualizations in `results/` folders
   - Try LLM interface with natural language queries

2. **Review documentation**:
   - Read [CLAUDE.md](CLAUDE.md) for project context
   - Study [MULTILEVEL-GUIDE.md](MULTILEVEL-GUIDE.md) for ABM architecture
   - Check use case examples in [EXAMPLE_CASES_PROMPTS.md](use_cases/mlu/EXAMPLE_CASES_PROMPTS.md)

3. **Set up your IDE**:
   - Install Python extensions (Pylance, Black formatter)
   - Install TypeScript/React extensions
   - Configure ESLint and Prettier

4. **Join team communication channels** (if applicable)

---

## 📞 Getting Help

- **Documentation**: Check `.md` files in project root
- **Issues**: Check existing GitHub issues
- **Questions**: Contact project lead or team members

---

## ✅ Setup Checklist

Copy this checklist and check off items as you complete them:

```
Backend Setup:
[ ] Python 3.12+ installed
[ ] Virtual environment created and activated
[ ] Python dependencies installed (pip install -r requirements.txt)
[ ] Backend simulations tested (MLU and CCA)
[ ] LLM interface tested

Frontend Setup:
[ ] Node.js 18+ installed
[ ] Frontend dependencies installed (npm install in frontend/)
[ ] Development server runs (npm run dev)
[ ] Production build succeeds (npm run build)
[ ] Theme toggle works (dark/light mode)

Environment:
[ ] .env file created (if needed)
[ ] .env.local created for frontend (if needed)
[ ] EO data path configured (or data access arranged)

Documentation:
[ ] Read CLAUDE.md
[ ] Read MULTILEVEL-GUIDE.md
[ ] Reviewed use case examples

Git:
[ ] Repository cloned
[ ] Feature branch created
[ ] .gitignore rules understood
```

---

## 🎉 You're Ready!

Once all checklist items are complete, you're ready to contribute to TRANSITION!

**Happy coding!** 🚀

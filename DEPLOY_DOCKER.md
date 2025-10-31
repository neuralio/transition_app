# TRANSITION Docker Deployment Guide

## 🐳 Dockerized Deployment for CentOS 7 Servers

This guide provides instructions for deploying the TRANSITION platform using Docker containers on CentOS 7, suitable for servers with multiple services running on different ports.

---

## 📋 Port Configuration

**Fixed Ports (No Fallback):**
- **Backend API**: `8003` (FastAPI + Uvicorn)
- **Frontend**: `3000` (Next.js) - **NO fallback to 3001**

---

## 🔧 Prerequisites

### 1. Install Docker on CentOS 7

```bash
# Update system packages
sudo yum update -y

# Install required packages
sudo yum install -y yum-utils device-mapper-persistent-data lvm2

# Add Docker repository
sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo

# Install Docker CE
sudo yum install -y docker-ce docker-ce-cli containerd.io

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Verify Docker installation
docker --version

# Add your user to docker group (optional - to run without sudo)
sudo usermod -aG docker $USER
# Log out and log back in for group changes to take effect
```

### 2. Install Docker Compose

```bash
# Download Docker Compose binary
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose

# Make it executable
sudo chmod +x /usr/local/bin/docker-compose

# Verify installation
docker-compose --version
```

### 3. Verify Data Path

Ensure your data directory exists and is accessible:

```bash
# Check if data path exists
ls -la /home/ggous/Downloads/PILOT_THESSALONIKI_DATA

# If using a different path, note it for .env configuration
```

---

## 🚀 Quick Start Deployment

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd transition
```

### Step 2: Configure Environment Variables

```bash
# Copy the Docker environment template
cp .env.docker .env

# Edit the .env file
nano .env  # or vim .env
```

**Required Configuration:**

```bash
# REQUIRED: Add your OpenAI API key
OPENAI_API_KEY=sk-...your_actual_key_here

# REQUIRED: Set your data path (default shown below)
DATA_PATH=/home/ggous/Downloads/PILOT_THESSALONIKI_DATA

# Optional: Sentinel Hub credentials (leave empty if not using)
SH_CLIENT_ID=
SH_CLIENT_SECRET=
```

### Step 3: Build Docker Images

```bash
# Build both backend and frontend images
docker-compose build

# This may take 5-15 minutes on first build
# Progress will be shown for each layer
```

### Step 4: Start Services

```bash
# Start all services in detached mode
docker-compose up -d

# View logs (optional)
docker-compose logs -f

# Press Ctrl+C to exit logs (containers keep running)
```

### Step 5: Verify Deployment

```bash
# Check running containers
docker-compose ps

# Expected output:
# NAME                    STATUS          PORTS
# transition-backend      Up (healthy)    0.0.0.0:8003->8003/tcp
# transition-frontend     Up (healthy)    0.0.0.0:3000->3000/tcp

# Test backend health
curl http://localhost:8003/api/health
# Expected: {"status":"healthy"}

# Test frontend (in browser or curl)
curl http://localhost:3000
# Expected: HTML content
```

**Access Application:**
- **Frontend**: http://your-server-ip:3000 or http://localhost:3000
- **Backend API**: http://your-server-ip:8003 or http://localhost:8003
- **API Documentation**: http://your-server-ip:8003/docs

---

## 🔄 Managing Containers

### View Logs

```bash
# All services
docker-compose logs -f

# Backend only
docker-compose logs -f backend

# Frontend only
docker-compose logs -f frontend

# Last 100 lines
docker-compose logs --tail=100 backend
```

### Restart Services

```bash
# Restart all services
docker-compose restart

# Restart specific service
docker-compose restart backend
docker-compose restart frontend
```

### Stop Services

```bash
# Stop all services (preserves containers)
docker-compose stop

# Start stopped services
docker-compose start
```

### Stop and Remove Containers

```bash
# Stop and remove containers (preserves images and volumes)
docker-compose down

# Remove containers, networks, and volumes
docker-compose down -v
```

### Rebuild After Code Changes

```bash
# Stop services
docker-compose down

# Rebuild images
docker-compose build --no-cache

# Start services
docker-compose up -d
```

---

## 📂 Directory Structure

```
transition/
├── Dockerfile.backend          # Backend container definition
├── Dockerfile.frontend         # Frontend container definition
├── docker-compose.yml          # Multi-container orchestration
├── .env                        # Environment variables (YOU CREATE THIS)
├── .env.docker                 # Template for .env
├── results/                    # Simulation results (auto-created)
├── logs/                       # Application logs (auto-created)
├── temp/                       # Temporary files (auto-created)
└── ...
```

**Mounted Volumes:**
- **Data (read-only)**: `/home/ggous/Downloads/PILOT_THESSALONIKI_DATA` → `/data` (inside container)
- **Results**: `./results` → `/app/results`
- **Logs**: `./logs` → `/app/logs`
- **Temp**: `./temp` → `/app/temp`

---

## 🔍 Troubleshooting

### Container Not Starting

```bash
# Check container status
docker-compose ps

# View detailed logs
docker-compose logs backend
docker-compose logs frontend

# Inspect container
docker inspect transition-backend
```

### Port Already in Use

```bash
# Check what's using port 8003
sudo netstat -tulpn | grep 8003

# Or using lsof
sudo lsof -i :8003

# If port 3000 is in use
sudo netstat -tulpn | grep 3000
```

**Solution**: Stop the conflicting service or change ports in `docker-compose.yml`

### Permission Denied Errors

```bash
# Ensure Docker is running
sudo systemctl status docker

# Add user to docker group (if not done)
sudo usermod -aG docker $USER
# Log out and log back in

# Check file permissions
ls -la /home/ggous/Downloads/PILOT_THESSALONIKI_DATA
```

### Data Path Not Found

```bash
# Verify data path in .env
cat .env | grep DATA_PATH

# Check if path exists
ls -la /home/ggous/Downloads/PILOT_THESSALONIKI_DATA

# Update .env with correct path if needed
nano .env
```

### Backend Health Check Failing

```bash
# Check backend logs
docker-compose logs backend

# Common issues:
# - Missing OPENAI_API_KEY in .env
# - Data path not accessible
# - Python dependencies installation failed

# Restart backend
docker-compose restart backend
```

### Frontend Not Connecting to Backend

```bash
# Verify backend is healthy
curl http://localhost:8003/api/health

# Check frontend logs
docker-compose logs frontend

# Ensure NEXT_PUBLIC_API_URL is correct in docker-compose.yml
# Should be: NEXT_PUBLIC_API_URL=http://localhost:8003
```

### Container Memory Issues (CentOS 7)

```bash
# Check container resource usage
docker stats

# If memory is constrained, add resource limits in docker-compose.yml:
# services:
#   backend:
#     mem_limit: 4g
#     memswap_limit: 4g
```

---

## 🔧 Advanced Configuration

### Custom Ports

If you need different ports, edit `docker-compose.yml`:

```yaml
services:
  backend:
    ports:
      - "YOUR_BACKEND_PORT:8003"  # Change left number only

  frontend:
    ports:
      - "YOUR_FRONTEND_PORT:3000"  # Change left number only
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:YOUR_BACKEND_PORT
```

### Production Mode (No Code Mounting)

For production, comment out volume mounts in `docker-compose.yml`:

```yaml
services:
  backend:
    volumes:
      - ${DATA_PATH}:/data:ro
      - ./results:/app/results
      - ./logs:/app/logs
      - ./temp:/app/temp
      # Comment out these lines for production:
      # - ./backend:/app/backend
      # - ./use_cases:/app/use_cases
      # - ./llm_interface:/app/llm_interface
```

### NGINX Reverse Proxy (Recommended for Production)

See `nginx.conf.example` for reverse proxy configuration.

---

## 🧪 Testing the Deployment

### Test Backend API

```bash
# Health check
curl http://localhost:8003/api/health

# API documentation
curl http://localhost:8003/docs

# Test query endpoint (requires frontend or curl with JSON)
curl -X POST http://localhost:8003/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "Show me land suitability for wheat"}'
```

### Test MLU Simulation (CLI)

```bash
# Enter backend container
docker exec -it transition-backend bash

# Inside container, run simulation
python use_cases/mlu/run_mlu.py --query mlu_04 --parcels 10 --scenario moderate

# Exit container
exit

# Check results
ls -la results/
```

### Test Frontend Access

1. Open browser: `http://your-server-ip:3000`
2. Draw a polygon on the map
3. Enter a query: "Simulate wheat under moderate scenario for 5 years with 10 parcels"
4. Verify results appear

---

## 📊 Monitoring

### Container Health

```bash
# Check health status
docker-compose ps

# Watch container stats (CPU, memory, network)
docker stats
```

### Application Logs

```bash
# Backend logs
docker-compose logs -f backend

# Frontend logs
docker-compose logs -f frontend

# Save logs to file
docker-compose logs backend > backend.log
docker-compose logs frontend > frontend.log
```

### Disk Usage

```bash
# Check Docker disk usage
docker system df

# Detailed view
docker system df -v

# Clean up unused resources
docker system prune -a --volumes
# WARNING: This removes all unused containers, images, and volumes
```

---

## 🔒 Security Considerations

### Firewall Configuration

```bash
# Open ports on CentOS 7 firewall
sudo firewall-cmd --permanent --add-port=8003/tcp
sudo firewall-cmd --permanent --add-port=3000/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

### Environment Variables

- **Never commit `.env` to version control**
- Store sensitive keys securely
- Use Docker secrets for production (see Docker Swarm documentation)

### Network Isolation

The `docker-compose.yml` creates an isolated bridge network (`transition-network`) for container communication.

---

## 📝 Common Commands Cheat Sheet

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f

# Rebuild images
docker-compose build --no-cache

# Check status
docker-compose ps

# Enter backend container
docker exec -it transition-backend bash

# Enter frontend container
docker exec -it transition-frontend sh

# Clean up everything
docker-compose down -v
docker system prune -a
```

---

## 🆘 Getting Help

If you encounter issues:

1. **Check logs**: `docker-compose logs -f`
2. **Verify environment**: `cat .env`
3. **Check data path**: `ls -la /home/ggous/Downloads/PILOT_THESSALONIKI_DATA`
4. **Test connectivity**: `curl http://localhost:8003/api/health`
5. **Consult documentation**: [CLAUDE.md](CLAUDE.md), [PLANNING.md](PLANNING.md), [TASKS.md](TASKS.md)

---

## 🎉 Success Indicators

Your deployment is successful when:

- ✅ `docker-compose ps` shows all containers as **Up (healthy)**
- ✅ `curl http://localhost:8003/api/health` returns `{"status":"healthy"}`
- ✅ Frontend accessible at `http://localhost:3000`
- ✅ You can run simulations through the UI
- ✅ Results appear in `./results/` directory

---

**Last Updated**: 2025-10-27
**Maintained By**: TRANSITION Development Team
**For Questions**: See [CLAUDE.md](CLAUDE.md) for AI assistant support

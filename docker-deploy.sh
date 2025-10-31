#!/bin/bash

# TRANSITION Docker Deployment Script
# Automates the deployment process for CentOS 7 servers

set -e  # Exit on error

echo "================================================"
echo "TRANSITION Docker Deployment Script"
echo "================================================"
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found!${NC}"
    echo "Creating .env from template..."

    if [ -f .env.docker ]; then
        cp .env.docker .env
        echo -e "${GREEN}✓ Created .env file from template${NC}"
        echo ""
        echo -e "${RED}IMPORTANT: Edit .env file and add your API_KEY!${NC}"
        echo "Run: nano .env"
        echo ""
        read -p "Press Enter after you've configured .env, or Ctrl+C to exit..."
    else
        echo -e "${RED}Error: .env.docker template not found!${NC}"
        exit 1
    fi
fi

# Check if API_KEY is set
if grep -q "your_api_key_here" .env; then
    echo -e "${RED}Error: API_KEY not configured in .env!${NC}"
    echo "Please edit .env and add your actual API key."
    exit 1
fi

echo "Checking Docker installation..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker first. See DEPLOY_DOCKER.md for instructions."
    exit 1
fi
echo -e "${GREEN}✓ Docker is installed${NC}"

echo "Checking Docker Compose installation..."
# Check for both 'docker compose' (v2) and 'docker-compose' (v1)
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
    echo -e "${GREEN}✓ Docker Compose (v2) is installed${NC}"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
    echo -e "${GREEN}✓ Docker Compose (v1) is installed${NC}"
else
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose first. See DEPLOY_DOCKER.md for instructions."
    exit 1
fi

# Check if Docker daemon is running
if ! docker info &> /dev/null; then
    echo -e "${RED}Error: Docker daemon is not running!${NC}"
    echo "Please start Docker: sudo systemctl start docker"
    exit 1
fi
echo -e "${GREEN}✓ Docker daemon is running${NC}"

echo ""
echo "Checking data path..."
DATA_PATH=$(grep "^DATA_PATH=" .env | cut -d'=' -f2)
if [ -z "$DATA_PATH" ]; then
    DATA_PATH="/home/TRANSITION_APP/transition/data"
    echo -e "${YELLOW}Warning: DATA_PATH not set in .env, using default: $DATA_PATH${NC}"
fi

if [ ! -d "$DATA_PATH" ]; then
    echo -e "${RED}Error: Data path not found: $DATA_PATH${NC}"
    echo "Please update DATA_PATH in .env file."
    exit 1
fi
echo -e "${GREEN}✓ Data path exists: $DATA_PATH${NC}"

echo ""
echo "================================================"
echo "Starting Docker Deployment"
echo "================================================"
echo ""

# Stop existing containers
echo "Stopping existing containers (if any)..."
$DOCKER_COMPOSE_CMD down 2>/dev/null || true
echo -e "${GREEN}✓ Stopped existing containers${NC}"

# Build images
echo ""
echo "Building Docker images (this may take 5-15 minutes)..."
$DOCKER_COMPOSE_CMD build --no-cache
echo -e "${GREEN}✓ Built Docker images${NC}"

# Start services
echo ""
echo "Starting services..."
$DOCKER_COMPOSE_CMD up -d
echo -e "${GREEN}✓ Started services${NC}"

# Wait for health checks
echo ""
echo "Waiting for services to become healthy..."
sleep 10

# Check backend health
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:8003/api/health &> /dev/null; then
        echo -e "${GREEN}✓ Backend is healthy${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for backend... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: Backend health check failed!${NC}"
    echo "Check logs: $DOCKER_COMPOSE_CMD logs backend"
    exit 1
fi

# Check frontend health
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s http://localhost:3000 &> /dev/null; then
        echo -e "${GREEN}✓ Frontend is healthy${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT+1))
    echo "Waiting for frontend... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo -e "${RED}Error: Frontend health check failed!${NC}"
    echo "Check logs: $DOCKER_COMPOSE_CMD logs frontend"
    exit 1
fi

echo ""
echo "================================================"
echo -e "${GREEN}Deployment Successful!${NC}"
echo "================================================"
echo ""
echo "Services are running:"
echo "  - Backend API:  http://localhost:8003"
echo "  - Frontend:     http://localhost:3000"
echo "  - API Docs:     http://localhost:8003/docs"
echo ""
echo "Useful commands:"
echo "  - View logs:    $DOCKER_COMPOSE_CMD logs -f"
echo "  - Stop:         $DOCKER_COMPOSE_CMD down"
echo "  - Restart:      $DOCKER_COMPOSE_CMD restart"
echo "  - Status:       $DOCKER_COMPOSE_CMD ps"
echo ""
echo "See DEPLOY_DOCKER.md for more information."

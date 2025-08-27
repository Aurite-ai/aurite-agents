#!/bin/bash

# This script tests the full Docker Compose setup including backend, frontend, and database connectivity.

# Exit immediately if a command exits with a non-zero status.
set -e

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Define variables
BACKEND_PORT=8000
FRONTEND_PORT=3000
MAX_RETRIES=30
RETRY_DELAY=2

echo -e "${YELLOW}Starting Docker Compose test...${NC}"
echo "================================"

# --- Cleanup any existing containers ---
echo -e "${YELLOW}Cleaning up any existing containers...${NC}"
docker compose down -v 2>/dev/null || true
echo "Cleanup complete."
echo "--------------------------------"

# --- Build and Start Services ---
echo -e "${YELLOW}Building and starting services...${NC}"
docker compose up -d --build
echo "Services started."
echo "--------------------------------"

# --- Wait for Backend ---
echo -e "${YELLOW}Waiting for backend to be ready...${NC}"
sleep 5
for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s http://localhost:$BACKEND_PORT/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Backend is ready!${NC}"
        break
    fi
    echo "Attempt $i/$MAX_RETRIES: Backend not ready yet. Retrying in $RETRY_DELAY seconds..."
    sleep $RETRY_DELAY

    if [ $i -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Backend failed to start after $MAX_RETRIES attempts.${NC}"
        echo "Backend logs:"
        docker compose logs backend
        docker compose down
        exit 1
    fi
done
echo "--------------------------------"

# --- Test Backend Health ---
echo -e "${YELLOW}Testing backend /health endpoint...${NC}"
HEALTH_RESPONSE=$(curl -s http://localhost:$BACKEND_PORT/health)
echo "Response: $HEALTH_RESPONSE"
if [[ $HEALTH_RESPONSE == *"\"status\":\"ok\""* ]] || [[ $HEALTH_RESPONSE == *"\"status\":\"healthy\""* ]]; then
    echo -e "${GREEN}✅ Backend health check PASSED${NC}"
else
    echo -e "${RED}❌ Backend health check FAILED${NC}"
    docker compose down
    exit 1
fi
echo "--------------------------------"

# --- Wait for Frontend ---
echo -e "${YELLOW}Waiting for frontend to be ready...${NC}"
for i in $(seq 1 $MAX_RETRIES); do
    if curl -f -s http://localhost:$FRONTEND_PORT > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Frontend is ready!${NC}"
        break
    fi
    echo "Attempt $i/$MAX_RETRIES: Frontend not ready yet. Retrying in $RETRY_DELAY seconds..."
    sleep $RETRY_DELAY

    if [ $i -eq $MAX_RETRIES ]; then
        echo -e "${RED}❌ Frontend failed to start after $MAX_RETRIES attempts.${NC}"
        echo "Frontend logs:"
        docker compose logs frontend
        docker compose down
        exit 1
    fi
done
echo "--------------------------------"

# --- Test Frontend ---
echo -e "${YELLOW}Testing frontend accessibility...${NC}"
FRONTEND_RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:$FRONTEND_PORT)
if [ "$FRONTEND_RESPONSE" = "200" ]; then
    echo -e "${GREEN}✅ Frontend is accessible (HTTP $FRONTEND_RESPONSE)${NC}"
else
    echo -e "${RED}❌ Frontend returned HTTP $FRONTEND_RESPONSE${NC}"
    docker compose logs frontend
    docker compose down
    exit 1
fi
echo "--------------------------------"

# --- Test Database Connectivity ---
echo -e "${YELLOW}Testing database connectivity through backend...${NC}"
# This assumes there's a database health endpoint or we can check via docker
DB_STATUS=$(docker compose exec -T postgres pg_isready -U postgres_user 2>&1)
if [[ $DB_STATUS == *"accepting connections"* ]]; then
    echo -e "${GREEN}✅ Database is accepting connections${NC}"
else
    echo -e "${RED}❌ Database connectivity issue${NC}"
    echo "Database status: $DB_STATUS"
    docker compose logs postgres
    docker compose down
    exit 1
fi
echo "--------------------------------"

# --- Show Service Status ---
echo -e "${YELLOW}Service Status:${NC}"
docker compose ps
echo "--------------------------------"

# --- Interactive Options ---
echo -e "${GREEN}🎉 All services are running successfully!${NC}"
echo ""
echo "You can now:"
echo "  - Access the backend API at: http://localhost:$BACKEND_PORT"
echo "  - Access the frontend at: http://localhost:$FRONTEND_PORT"
echo "  - View logs: docker compose logs -f [service_name]"
echo ""
read -p "Press 'q' to stop and clean up, or any other key to keep services running: " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Qq]$ ]]; then
    echo -e "${YELLOW}Stopping and cleaning up services...${NC}"
    docker compose down
    echo -e "${GREEN}Cleanup complete.${NC}"
else
    echo -e "${GREEN}Services are still running. To stop them later, run: docker compose down${NC}"
fi

echo "================================"
echo -e "${GREEN}Docker Compose test completed!${NC}"

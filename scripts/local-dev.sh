#!/bin/bash

# Exit on error
set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
ORCHESTRATOR_PORT=8000
LOG_LEVEL=INFO
COMMAND=

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --port)
      ORCHESTRATOR_PORT="$2"
      shift 2
      ;;
    --log-level)
      LOG_LEVEL="$2"
      shift 2
      ;;
    start|stop|restart|logs|status|start_orchestrator|stop_orchestrator|start_mock_models|stop_mock_models)
      COMMAND=$1
      shift
      ;;
    *)
      echo "Unknown option or command: $1"
      show_usage
      ;;
  esac
done

# Function to display usage
function show_usage() {
  echo "Local Development Environment Manager"
  echo "Usage: $0 [options] <command>"
  echo ""
  echo "Commands:"
  echo "  start             Start all services"
  echo "  stop              Stop all services"
  echo "  restart           Restart all services"
  echo "  logs              Show logs"
  echo "  status            Show status of services"
  echo "  start_orchestrator   Start only the orchestrator"
  echo "  stop_orchestrator    Stop only the orchestrator"
  echo "  start_mock_models    Start only the mock models"
  echo "  stop_mock_models     Stop only the mock models"
  echo ""
  echo "Options:"
  echo "  --port PORT       Port for the orchestrator (default: 8000)"
  echo "  --log-level LEVEL Log level (default: INFO)"
  exit 1
}

# Function to start services
function start_services() {
  echo -e "${GREEN}Starting local development environment...${NC}"
  
  # Create necessary directories
  mkdir -p logs
  
  # Start services
  ORCHESTRATOR_PORT=$ORCHESTRATOR_PORT LOG_LEVEL=$LOG_LEVEL \
    docker-compose up -d --build
  
  echo -e "\n${GREEN}Services started successfully!${NC}"
  echo -e "Orchestrator: http://localhost:${ORCHESTRATOR_PORT}"
  echo -e "Mock Model 1: http://localhost:8001/health"
  echo -e "Mock Model 2: http://localhost:8002/health"
}

# Function to stop services
function stop_services() {
  echo -e "${YELLOW}Stopping services...${NC}"
  docker-compose down
  echo -e "${GREEN}Services stopped.${NC}"
}

# Function to show logs
function show_logs() {
  docker-compose logs -f
}

# Function to show status
function show_status() {
  echo -e "${GREEN}=== Service Status ===${NC}"
  docker-compose ps
  
  echo -e "\n${GREEN}=== Endpoints ===${NC}"
  echo "Orchestrator: http://localhost:${ORCHESTRATOR_PORT}/health"
  echo "Mock Model 1: http://localhost:8001/health"
  echo "Mock Model 2: http://localhost:8002/health"
}

# Function to start only the orchestrator
function start_orchestrator() {
  echo -e "${GREEN}Starting orchestrator...${NC}"
  ORCHESTRATOR_PORT=$ORCHESTRATOR_PORT LOG_LEVEL=$LOG_LEVEL \
    docker-compose up -d --build orchestrator
  echo -e "\n${GREEN}Orchestrator started successfully!${NC}"
  echo -e "Orchestrator: http://localhost:${ORCHESTRATOR_PORT}"
}

# Function to stop only the orchestrator
function stop_orchestrator() {
  echo -e "${YELLOW}Stopping orchestrator...${NC}"
  docker-compose stop orchestrator
  docker-compose rm -f orchestrator
  echo -e "${GREEN}Orchestrator stopped.${NC}"
}

# Function to start only the mock models
function start_mock_models() {
  echo -e "${GREEN}Starting mock models...${NC}"
  docker-compose up -d --build mock-model-1 mock-model-2
  echo -e "\n${GREEN}Mock models started successfully!${NC}"
  echo -e "Mock Model 1: http://localhost:8001/health"
  echo -e "Mock Model 2: http://localhost:8002/health"
}

# Function to stop only the mock models
function stop_mock_models() {
  echo -e "${YELLOW}Stopping mock models...${NC}"
  docker-compose stop mock-model-1 mock-model-2
  docker-compose rm -f mock-model-1 mock-model-2
  echo -e "${GREEN}Mock models stopped.${NC}"
}

# Main command execution
case "$COMMAND" in
  start)
    start_services
    ;;
  stop)
    stop_services
    ;;
  restart)
    stop_services
    start_services
    ;;
  logs)
    show_logs
    ;;
  status)
    show_status
    ;;
  start_orchestrator)
    start_orchestrator
    ;;
  stop_orchestrator)
    stop_orchestrator
    ;;
  start_mock_models)
    start_mock_models
    ;;
  stop_mock_models)
    stop_mock_models
    ;;
  *)
    show_usage
    ;;
esac

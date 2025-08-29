#!/bin/bash

# RAG Implementation Deployment Script

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    print_status "Docker and Docker Compose are installed."
}

# Check if .env file exists
check_env() {
    if [ ! -f ".env" ]; then
        print_warning ".env file not found. Creating from template..."
        cp .env.example .env
        print_warning "Please edit .env file and add your OpenAI API key before continuing."
        read -p "Press Enter to continue after editing .env file..."
    fi
    
    # Check if OPENAI_API_KEY is set
    if ! grep -q "OPENAI_API_KEY=.*[^[:space:]]" .env; then
        print_error "OPENAI_API_KEY is not set in .env file. Please add your OpenAI API key."
        exit 1
    fi
    
    print_status "Environment configuration is ready."
}

# Build containers
build_containers() {
    print_status "Building containers..."
    docker-compose build
    print_status "Containers built successfully."
}

# Start services
start_services() {
    print_status "Starting services..."
    docker-compose up -d
    print_status "Services started successfully."
}

# Check service health
check_health() {
    print_status "Checking service health..."
    
    # Wait for services to start
    sleep 10
    
    # Check API health
    for i in {1..30}; do
        if curl -f http://localhost:8000/ &> /dev/null; then
            print_status "API service is healthy."
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "API service failed to start properly."
            docker-compose logs api
            exit 1
        fi
        sleep 2
    done
    
    # Check Web health
    for i in {1..30}; do
        if curl -f http://localhost:3000/ &> /dev/null; then
            print_status "Web service is healthy."
            break
        fi
        if [ $i -eq 30 ]; then
            print_error "Web service failed to start properly."
            docker-compose logs web
            exit 1
        fi
        sleep 2
    done
}

# Show service information
show_info() {
    print_status "Deployment completed successfully!"
    echo ""
    echo "Services are running:"
    echo "  - Web Frontend: http://localhost:3000"
    echo "  - API Backend: http://localhost:8000"
    echo "  - API Documentation: http://localhost:8000/docs"
    echo ""
    echo "Useful commands:"
    echo "  - View logs: docker-compose logs -f"
    echo "  - Stop services: docker-compose down"
    echo "  - Restart services: docker-compose restart"
    echo ""
}

# Main deployment function
deploy() {
    print_status "Starting RAG Implementation deployment..."
    
    check_docker
    check_env
    build_containers
    start_services
    check_health
    show_info
}

# Handle command line arguments
case "${1:-deploy}" in
    "deploy")
        deploy
        ;;
    "build")
        build_containers
        ;;
    "start")
        start_services
        ;;
    "stop")
        print_status "Stopping services..."
        docker-compose down
        ;;
    "restart")
        print_status "Restarting services..."
        docker-compose restart
        ;;
    "logs")
        docker-compose logs -f
        ;;
    "clean")
        print_status "Cleaning up..."
        docker-compose down --rmi all --volumes --remove-orphans
        docker system prune -f
        ;;
    *)
        echo "Usage: $0 {deploy|build|start|stop|restart|logs|clean}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Full deployment (default)"
        echo "  build   - Build containers only"
        echo "  start   - Start services"
        echo "  stop    - Stop services"
        echo "  restart - Restart services"
        echo "  logs    - Show logs"
        echo "  clean   - Clean up containers and images"
        exit 1
        ;;
esac
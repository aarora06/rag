# Makefile for RAG Implementation Docker Management

.PHONY: help build up down logs clean restart api-logs web-logs

# Default target
help:
	@echo "Available commands:"
	@echo "  build     - Build all containers"
	@echo "  up        - Start all services"
	@echo "  down      - Stop all services"
	@echo "  restart   - Restart all services"
	@echo "  logs      - Show logs for all services"
	@echo "  api-logs  - Show API container logs"
	@echo "  web-logs  - Show Web container logs"
	@echo "  clean     - Remove containers and images"
	@echo "  help      - Show this help message"

# Build all containers
build:
	docker-compose build

# Start all services
up:
	docker-compose up -d

# Stop all services
down:
	docker-compose down

# Restart all services
restart: down up

# Show logs for all services
logs:
	docker-compose logs -f

# Show API container logs
api-logs:
	docker-compose logs -f api

# Show Web container logs
web-logs:
	docker-compose logs -f web

# Clean up containers and images
clean:
	docker-compose down --rmi all --volumes --remove-orphans
	docker system prune -f

# Development commands
dev-up:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml up

dev-build:
	docker-compose -f docker-compose.yml -f docker-compose.dev.yml build
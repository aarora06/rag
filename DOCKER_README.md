# Docker Deployment Guide

This guide explains how to deploy the RAG Implementation using Docker containers.

## Architecture

The application consists of two separate containers:
- **API Container**: FastAPI backend with RAG functionality
- **Web Container**: React frontend served by Nginx

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

## Quick Start

1. **Clone and navigate to the project directory**
   ```bash
   cd rag_implementation
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env file and add your OpenAI API key
   ```

3. **Build and run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Access the applications**
   - Web Frontend: http://localhost:3000
   - API Backend: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## Individual Container Deployment

### API Container

```bash
# Build the API container
cd api
docker build -t rag-api .

# Run the API container
docker run -d \
  --name rag-api \
  -p 8000:8000 \
  -e OPENAI_API_KEY=your_key_here \
  -e API_KEY=your_api_key_here \
  -v $(pwd)/knowledge_base:/app/knowledge_base \
  -v $(pwd)/vector_db:/app/vector_db \
  rag-api
```

### Web Container

```bash
# Build the web container
cd web/my-react-app
docker build -t rag-web .

# Run the web container
docker run -d \
  --name rag-web \
  -p 3000:80 \
  rag-web
```

## Environment Variables

### API Container
- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `API_KEY`: API key for authentication (optional)

### Web Container
No environment variables required for basic setup.

## Volumes

The API container uses volumes to persist:
- `knowledge_base/`: Document storage
- `vector_db/`: Vector database storage

## Networking

Both containers are connected via a custom Docker network (`rag-network`) for internal communication.

## Health Checks

Both containers include health checks:
- API: Checks `/` endpoint
- Web: Checks root path served by Nginx

## Production Considerations

1. **Security**
   - Use proper API keys
   - Configure CORS appropriately
   - Use HTTPS in production

2. **Scaling**
   - Consider using Docker Swarm or Kubernetes
   - Implement load balancing for multiple API instances

3. **Monitoring**
   - Add logging configuration
   - Implement monitoring and alerting

4. **Data Persistence**
   - Use named volumes or external storage for production
   - Implement backup strategies for vector database

## Troubleshooting

### Common Issues

1. **API fails to start**
   - Check if OPENAI_API_KEY is set correctly
   - Verify port 8000 is not in use

2. **Web container can't reach API**
   - Ensure both containers are on the same network
   - Check API container is healthy

3. **Permission issues with volumes**
   - Ensure proper file permissions on host directories

### Logs

```bash
# View API logs
docker logs rag-api

# View Web logs
docker logs rag-web

# View all services logs
docker-compose logs
```

## Development

For development with hot reloading:

```bash
# API development
cd api
docker run -it --rm \
  -p 8000:8000 \
  -v $(pwd):/app \
  -e OPENAI_API_KEY=your_key \
  python:3.11-slim \
  bash -c "cd /app && pip install -r requirements.txt && uvicorn api:app --host 0.0.0.0 --port 8000 --reload"

# Web development
cd web/my-react-app
docker run -it --rm \
  -p 3000:3000 \
  -v $(pwd):/app \
  -w /app \
  node:18-alpine \
  npm start
```
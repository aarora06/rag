# RAG Implementation

A comprehensive Retrieval-Augmented Generation (RAG) system with hierarchical document organization and multi-level retrieval capabilities.

## Architecture

This application consists of two main components:

- **API Backend**: FastAPI-based service providing RAG functionality with hierarchical document retrieval
- **Web Frontend**: React-based user interface for interacting with the RAG system

## Features

- **Hierarchical Document Organization**: Documents organized by company, department, and employee levels
- **Multi-level Retrieval**: Intelligent retrieval from multiple organizational levels
- **Vector Database**: ChromaDB for efficient similarity search
- **OpenAI Integration**: GPT-4 powered responses
- **RESTful API**: FastAPI with automatic documentation
- **Modern Web UI**: React-based frontend
- **Docker Support**: Containerized deployment for easy scaling

## Quick Start with Docker (Recommended)

### Prerequisites
- Docker and Docker Compose
- OpenAI API key

### Deployment

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd rag_implementation
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

3. **Deploy with Docker Compose**
   ```bash
   # Using PowerShell (Windows)
   .\deploy.ps1

   # Or using Docker Compose directly
   docker-compose up --build -d
   ```

4. **Access the applications**
   - Web Frontend: http://localhost:3000
   - API Backend: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

### Docker Commands

```bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down

# Rebuild containers
docker-compose up --build

# Clean up
docker-compose down --rmi all --volumes
```

## Manual Installation

### API Backend

1. **Navigate to API directory**
   ```bash
   cd api
   ```

2. **Create virtual environment**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and add your OpenAI API key
   ```

5. **Run the API**
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

### Web Frontend

1. **Navigate to web directory**
   ```bash
   cd web/my-react-app
   ```

2. **Install dependencies**
   ```bash
   npm install
   ```

3. **Start development server**
   ```bash
   npm start
   ```

## API Usage

### Authentication
Include your API key in the request headers:
```
X-API-Key: your_api_key_here
```

### Chat Endpoint
```bash
curl -X POST "http://localhost:8000/chat/" \
  -H "X-API-Key: your_api_key" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the company policy?",
    "company": "company_a",
    "department": "department_x",
    "employee": "employee_1",
    "chat_history": []
  }'
```

## Document Organization

Documents should be organized in the following hierarchy:
```
knowledge_base/
├── company_a/
│   ├── company_policy.md
│   ├── department_x/
│   │   ├── dept_guidelines.md
│   │   └── employee_1/
│   │       └── personal_docs.md
│   └── department_y/
│       └── employee_2/
│           └── employee_docs.md
└── general_docs/
    └── overview.md
```

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `API_KEY`: API authentication key (optional)
- `MODEL`: OpenAI model to use (default: gpt-4o-mini)

### File Structure

```
rag_implementation/
├── api/                    # FastAPI backend
│   ├── Dockerfile         # API container configuration
│   ├── requirements.txt   # Python dependencies
│   ├── api.py            # Main API application
│   ├── config.py         # Configuration settings
│   ├── loading.py        # Document loading logic
│   ├── retrieval.py      # Retrieval logic
│   └── knowledge_base/   # Document storage
├── web/                   # React frontend
│   └── my-react-app/
│       ├── Dockerfile    # Web container configuration
│       ├── package.json  # Node.js dependencies
│       └── src/          # React source code
├── docker-compose.yml     # Multi-container orchestration
├── deploy.ps1            # PowerShell deployment script
└── README.md             # This file
```

## Development

### API Development
```bash
cd api
docker run -it --rm \
  -p 8000:8000 \
  -v $(pwd):/app \
  -e OPENAI_API_KEY=your_key \
  python:3.11-slim \
  bash -c "cd /app && pip install -r requirements.txt && uvicorn api:app --host 0.0.0.0 --port 8000 --reload"
```

### Web Development
```bash
cd web/my-react-app
docker run -it --rm \
  -p 3000:3000 \
  -v $(pwd):/app \
  -w /app \
  node:18-alpine \
  npm start
```

## Production Deployment

For production deployment, consider:

1. **Security**
   - Use proper API keys and secrets management
   - Configure CORS appropriately
   - Enable HTTPS

2. **Scaling**
   - Use container orchestration (Kubernetes, Docker Swarm)
   - Implement load balancing
   - Set up monitoring and logging

3. **Data Persistence**
   - Use external storage for vector database
   - Implement backup strategies
   - Consider database clustering

## Troubleshooting

### Common Issues

1. **API fails to start**: Check OpenAI API key configuration
2. **No documents found**: Verify document organization in knowledge_base/
3. **Cross-company contamination**: Check document metadata and filtering logic

### Logs
```bash
# Docker logs
docker-compose logs api
docker-compose logs web

# Application logs
tail -f api/logs/app.log
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
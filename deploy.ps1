# RAG Implementation Deployment Script (PowerShell)

param(
    [Parameter(Position=0)]
    [ValidateSet("deploy", "build", "start", "stop", "restart", "logs", "clean")]
    [string]$Command = "deploy"
)

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor Green
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor Yellow
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor Red
}

# Check if Docker is installed
function Test-Docker {
    try {
        docker --version | Out-Null
        docker-compose --version | Out-Null
        Write-Status "Docker and Docker Compose are installed."
        return $true
    }
    catch {
        Write-Error "Docker or Docker Compose is not installed. Please install Docker Desktop first."
        return $false
    }
}

# Check if .env file exists
function Test-Environment {
    if (-not (Test-Path ".env")) {
        Write-Warning ".env file not found. Creating from template..."
        Copy-Item ".env.example" ".env"
        Write-Warning "Please edit .env file and add your OpenAI API key before continuing."
        Read-Host "Press Enter to continue after editing .env file"
    }
    
    # Check if OPENAI_API_KEY is set
    $envContent = Get-Content ".env" -Raw
    if (-not ($envContent -match "OPENAI_API_KEY=.+")) {
        Write-Error "OPENAI_API_KEY is not set in .env file. Please add your OpenAI API key."
        return $false
    }
    
    Write-Status "Environment configuration is ready."
    return $true
}

# Build containers
function Build-Containers {
    Write-Status "Building containers..."
    docker-compose build
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Containers built successfully."
        return $true
    } else {
        Write-Error "Failed to build containers."
        return $false
    }
}

# Start services
function Start-Services {
    Write-Status "Starting services..."
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Status "Services started successfully."
        return $true
    } else {
        Write-Error "Failed to start services."
        return $false
    }
}

# Check service health
function Test-ServiceHealth {
    Write-Status "Checking service health..."
    
    # Wait for services to start
    Start-Sleep -Seconds 10
    
    # Check API health
    $apiHealthy = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Status "API service is healthy."
                $apiHealthy = $true
                break
            }
        }
        catch {
            # Continue trying
        }
        
        if ($i -eq 30) {
            Write-Error "API service failed to start properly."
            docker-compose logs api
            return $false
        }
        Start-Sleep -Seconds 2
    }
    
    # Check Web health
    $webHealthy = $false
    for ($i = 1; $i -le 30; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000/" -TimeoutSec 5 -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                Write-Status "Web service is healthy."
                $webHealthy = $true
                break
            }
        }
        catch {
            # Continue trying
        }
        
        if ($i -eq 30) {
            Write-Error "Web service failed to start properly."
            docker-compose logs web
            return $false
        }
        Start-Sleep -Seconds 2
    }
    
    return ($apiHealthy -and $webHealthy)
}

# Show service information
function Show-ServiceInfo {
    Write-Status "Deployment completed successfully!"
    Write-Host ""
    Write-Host "Services are running:"
    Write-Host "  - Web Frontend: http://localhost:3000"
    Write-Host "  - API Backend: http://localhost:8000"
    Write-Host "  - API Documentation: http://localhost:8000/docs"
    Write-Host ""
    Write-Host "Useful commands:"
    Write-Host "  - View logs: docker-compose logs -f"
    Write-Host "  - Stop services: docker-compose down"
    Write-Host "  - Restart services: docker-compose restart"
    Write-Host ""
}

# Main deployment function
function Start-Deployment {
    Write-Status "Starting RAG Implementation deployment..."
    
    if (-not (Test-Docker)) { exit 1 }
    if (-not (Test-Environment)) { exit 1 }
    if (-not (Build-Containers)) { exit 1 }
    if (-not (Start-Services)) { exit 1 }
    if (-not (Test-ServiceHealth)) { exit 1 }
    
    Show-ServiceInfo
}

# Handle commands
switch ($Command) {
    "deploy" {
        Start-Deployment
    }
    "build" {
        Build-Containers
    }
    "start" {
        Start-Services
    }
    "stop" {
        Write-Status "Stopping services..."
        docker-compose down
    }
    "restart" {
        Write-Status "Restarting services..."
        docker-compose restart
    }
    "logs" {
        docker-compose logs -f
    }
    "clean" {
        Write-Status "Cleaning up..."
        docker-compose down --rmi all --volumes --remove-orphans
        docker system prune -f
    }
    default {
        Write-Host "Usage: .\deploy.ps1 [deploy|build|start|stop|restart|logs|clean]"
        Write-Host ""
        Write-Host "Commands:"
        Write-Host "  deploy  - Full deployment (default)"
        Write-Host "  build   - Build containers only"
        Write-Host "  start   - Start services"
        Write-Host "  stop    - Stop services"
        Write-Host "  restart - Restart services"
        Write-Host "  logs    - Show logs"
        Write-Host "  clean   - Clean up containers and images"
    }
}
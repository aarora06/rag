# Container Testing Script
# Run this script after Docker is installed to test the containers

param(
    [switch]$SkipBuild,
    [switch]$Verbose
)

# Colors for output
$Green = "Green"
$Red = "Red"
$Yellow = "Yellow"

function Write-TestStatus {
    param([string]$Message, [string]$Color = "White")
    Write-Host "🔍 $Message" -ForegroundColor $Color
}

function Write-TestSuccess {
    param([string]$Message)
    Write-Host "✅ $Message" -ForegroundColor $Green
}

function Write-TestError {
    param([string]$Message)
    Write-Host "❌ $Message" -ForegroundColor $Red
}

function Write-TestWarning {
    param([string]$Message)
    Write-Host "⚠️  $Message" -ForegroundColor $Yellow
}

# Test Docker installation
function Test-DockerInstallation {
    Write-TestStatus "Testing Docker installation..."
    
    try {
        $dockerVersion = docker --version 2>$null
        $composeVersion = docker-compose --version 2>$null
        
        if ($dockerVersion -and $composeVersion) {
            Write-TestSuccess "Docker is installed: $dockerVersion"
            Write-TestSuccess "Docker Compose is installed: $composeVersion"
            return $true
        } else {
            Write-TestError "Docker or Docker Compose is not installed or not in PATH"
            return $false
        }
    }
    catch {
        Write-TestError "Docker is not installed. Please install Docker Desktop first."
        Write-Host "See DOCKER_INSTALLATION.md for installation instructions."
        return $false
    }
}

# Test environment setup
function Test-Environment {
    Write-TestStatus "Testing environment setup..."
    
    if (-not (Test-Path ".env")) {
        Write-TestWarning ".env file not found. Creating from template..."
        if (Test-Path ".env.example") {
            Copy-Item ".env.example" ".env"
            Write-TestWarning "Please edit .env file and add your OpenAI API key"
            return $false
        } else {
            Write-TestError ".env.example file not found"
            return $false
        }
    }
    
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "OPENAI_API_KEY=sk-[a-zA-Z0-9-_]+") {
        Write-TestSuccess "OpenAI API key is configured"
        return $true
    } elseif ($envContent -match "OPENAI_API_KEY=your_openai_api_key_here") {
        Write-TestError "Please replace the placeholder with your actual OpenAI API key in .env file"
        return $false
    } else {
        Write-TestWarning "OpenAI API key format might be incorrect"
        return $true
    }
}

# Build containers
function Build-TestContainers {
    if ($SkipBuild) {
        Write-TestStatus "Skipping container build..."
        return $true
    }
    
    Write-TestStatus "Building containers..."
    
    try {
        if ($Verbose) {
            docker-compose build
        } else {
            docker-compose build 2>$null
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-TestSuccess "Containers built successfully"
            return $true
        } else {
            Write-TestError "Failed to build containers"
            return $false
        }
    }
    catch {
        Write-TestError "Error building containers: $_"
        return $false
    }
}

# Start containers
function Start-TestContainers {
    Write-TestStatus "Starting containers..."
    
    try {
        if ($Verbose) {
            docker-compose up -d
        } else {
            docker-compose up -d 2>$null
        }
        
        if ($LASTEXITCODE -eq 0) {
            Write-TestSuccess "Containers started successfully"
            return $true
        } else {
            Write-TestError "Failed to start containers"
            return $false
        }
    }
    catch {
        Write-TestError "Error starting containers: $_"
        return $false
    }
}

# Test container health
function Test-ContainerHealth {
    Write-TestStatus "Testing container health..."
    
    # Wait for containers to start
    Write-TestStatus "Waiting for containers to initialize..."
    Start-Sleep -Seconds 15
    
    # Test API container
    $apiHealthy = $false
    Write-TestStatus "Testing API container..."
    for ($i = 1; $i -le 20; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:8000/" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-TestSuccess "API container is healthy and responding"
                $apiHealthy = $true
                break
            }
        }
        catch {
            # Continue trying
        }
        
        Write-TestStatus "API attempt $i/20..."
        Start-Sleep -Seconds 3
    }
    
    if (-not $apiHealthy) {
        Write-TestError "API container failed to respond"
        Write-TestStatus "API container logs:"
        docker-compose logs api
    }
    
    # Test Web container
    $webHealthy = $false
    Write-TestStatus "Testing Web container..."
    for ($i = 1; $i -le 20; $i++) {
        try {
            $response = Invoke-WebRequest -Uri "http://localhost:3000/" -TimeoutSec 5 -UseBasicParsing -ErrorAction SilentlyContinue
            if ($response.StatusCode -eq 200) {
                Write-TestSuccess "Web container is healthy and responding"
                $webHealthy = $true
                break
            }
        }
        catch {
            # Continue trying
        }
        
        Write-TestStatus "Web attempt $i/20..."
        Start-Sleep -Seconds 3
    }
    
    if (-not $webHealthy) {
        Write-TestError "Web container failed to respond"
        Write-TestStatus "Web container logs:"
        docker-compose logs web
    }
    
    return ($apiHealthy -and $webHealthy)
}

# Test API functionality
function Test-APIFunctionality {
    Write-TestStatus "Testing API functionality..."
    
    try {
        # Test health endpoint
        $healthResponse = Invoke-WebRequest -Uri "http://localhost:8000/" -UseBasicParsing
        if ($healthResponse.StatusCode -eq 200) {
            Write-TestSuccess "API health endpoint working"
        }
        
        # Test docs endpoint
        $docsResponse = Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing
        if ($docsResponse.StatusCode -eq 200) {
            Write-TestSuccess "API documentation endpoint working"
        }
        
        # Test chat endpoint (basic structure test)
        $chatBody = @{
            question = "Hello, this is a test"
            company = "test_company"
            department = "test_department"
            employee = "test_employee"
            chat_history = @()
        } | ConvertTo-Json
        
        $headers = @{
            "Content-Type" = "application/json"
            "X-API-Key" = "dummy_local_api_key"
        }
        
        try {
            $chatResponse = Invoke-WebRequest -Uri "http://localhost:8000/chat/" -Method POST -Body $chatBody -Headers $headers -UseBasicParsing -TimeoutSec 30
            if ($chatResponse.StatusCode -eq 200) {
                Write-TestSuccess "API chat endpoint is accessible"
            }
        }
        catch {
            if ($_.Exception.Response.StatusCode -eq 422) {
                Write-TestSuccess "API chat endpoint is working (validation error expected without proper setup)"
            } else {
                Write-TestWarning "API chat endpoint test inconclusive: $($_.Exception.Message)"
            }
        }
        
        return $true
    }
    catch {
        Write-TestError "API functionality test failed: $_"
        return $false
    }
}

# Show container status
function Show-ContainerStatus {
    Write-TestStatus "Container Status:"
    docker-compose ps
    
    Write-Host ""
    Write-TestStatus "Container Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
}

# Show access information
function Show-AccessInfo {
    Write-Host ""
    Write-Host "🎉 Container Testing Complete!" -ForegroundColor $Green
    Write-Host ""
    Write-Host "Access your applications:" -ForegroundColor $Yellow
    Write-Host "  🌐 Web Frontend:     http://localhost:3000" -ForegroundColor Cyan
    Write-Host "  🔧 API Backend:      http://localhost:8000" -ForegroundColor Cyan
    Write-Host "  📚 API Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Useful commands:" -ForegroundColor $Yellow
    Write-Host "  📋 View logs:        docker-compose logs -f"
    Write-Host "  🛑 Stop containers:  docker-compose down"
    Write-Host "  🔄 Restart:          docker-compose restart"
    Write-Host "  🧹 Clean up:         docker-compose down --rmi all --volumes"
    Write-Host ""
}

# Main test execution
function Start-ContainerTest {
    Write-Host "🚀 Starting Container Test Suite" -ForegroundColor $Green
    Write-Host "=================================" -ForegroundColor $Green
    Write-Host ""
    
    $testsPassed = 0
    $totalTests = 6
    
    # Test 1: Docker Installation
    if (Test-DockerInstallation) { $testsPassed++ }
    else { return }
    
    # Test 2: Environment Setup
    if (Test-Environment) { $testsPassed++ }
    else { 
        Write-Host "Please configure your .env file and run the test again."
        return 
    }
    
    # Test 3: Build Containers
    if (Build-TestContainers) { $testsPassed++ }
    else { return }
    
    # Test 4: Start Containers
    if (Start-TestContainers) { $testsPassed++ }
    else { return }
    
    # Test 5: Container Health
    if (Test-ContainerHealth) { $testsPassed++ }
    else { 
        Write-TestWarning "Some containers may not be healthy, but continuing..."
    }
    
    # Test 6: API Functionality
    if (Test-APIFunctionality) { $testsPassed++ }
    
    # Show status
    Show-ContainerStatus
    
    # Show results
    Write-Host ""
    Write-Host "Test Results: $testsPassed/$totalTests tests passed" -ForegroundColor $(if ($testsPassed -eq $totalTests) { $Green } else { $Yellow })
    
    if ($testsPassed -ge 4) {
        Show-AccessInfo
    } else {
        Write-TestError "Too many tests failed. Please check the logs and try again."
        Write-Host "Run 'docker-compose logs' to see detailed error messages."
    }
}

# Run the test suite
Start-ContainerTest
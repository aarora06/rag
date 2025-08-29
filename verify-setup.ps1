# Setup Verification Script
# Run this script to verify your system is ready for container deployment

Write-Host "🔍 RAG Implementation Setup Verification" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Green
Write-Host ""

$allGood = $true

# Check 1: Docker Installation
Write-Host "1. Checking Docker installation..." -ForegroundColor Yellow
try {
    $dockerVersion = docker --version 2>$null
    $composeVersion = docker-compose --version 2>$null
    
    if ($dockerVersion -and $composeVersion) {
        Write-Host "   ✅ Docker installed: $dockerVersion" -ForegroundColor Green
        Write-Host "   ✅ Docker Compose installed: $composeVersion" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Docker or Docker Compose not found" -ForegroundColor Red
        Write-Host "   📖 See DOCKER_INSTALLATION.md for installation instructions" -ForegroundColor Cyan
        $allGood = $false
    }
}
catch {
    Write-Host "   ❌ Docker not installed or not in PATH" -ForegroundColor Red
    Write-Host "   📖 See DOCKER_INSTALLATION.md for installation instructions" -ForegroundColor Cyan
    $allGood = $false
}

Write-Host ""

# Check 2: Docker Service Status
Write-Host "2. Checking Docker service status..." -ForegroundColor Yellow
try {
    docker info 2>$null | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "   ✅ Docker service is running" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Docker service is not running" -ForegroundColor Red
        Write-Host "   💡 Start Docker Desktop and try again" -ForegroundColor Cyan
        $allGood = $false
    }
}
catch {
    Write-Host "   ❌ Cannot connect to Docker service" -ForegroundColor Red
    Write-Host "   💡 Make sure Docker Desktop is running" -ForegroundColor Cyan
    $allGood = $false
}

Write-Host ""

# Check 3: Project Files
Write-Host "3. Checking project files..." -ForegroundColor Yellow

$requiredFiles = @(
    "docker-compose.yml",
    "api\Dockerfile",
    "api\requirements.txt",
    "web\my-react-app\Dockerfile",
    "web\my-react-app\package.json"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "   ✅ Found: $file" -ForegroundColor Green
    } else {
        Write-Host "   ❌ Missing: $file" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""

# Check 4: Environment Configuration
Write-Host "4. Checking environment configuration..." -ForegroundColor Yellow

if (Test-Path ".env") {
    Write-Host "   ✅ .env file exists" -ForegroundColor Green
    
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "OPENAI_API_KEY=sk-[a-zA-Z0-9-_]+") {
        Write-Host "   ✅ OpenAI API key is configured" -ForegroundColor Green
    } elseif ($envContent -match "OPENAI_API_KEY=your_openai_api_key_here") {
        Write-Host "   ⚠️  OpenAI API key needs to be updated" -ForegroundColor Yellow
        Write-Host "   💡 Edit .env file and replace placeholder with your actual API key" -ForegroundColor Cyan
        $allGood = $false
    } else {
        Write-Host "   ⚠️  OpenAI API key format might be incorrect" -ForegroundColor Yellow
    }
} else {
    Write-Host "   ⚠️  .env file not found" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "   💡 Creating .env from template..." -ForegroundColor Cyan
        Copy-Item ".env.example" ".env"
        Write-Host "   ✅ .env file created from template" -ForegroundColor Green
        Write-Host "   💡 Please edit .env file and add your OpenAI API key" -ForegroundColor Cyan
        $allGood = $false
    } else {
        Write-Host "   ❌ .env.example template not found" -ForegroundColor Red
        $allGood = $false
    }
}

Write-Host ""

# Check 5: Port Availability
Write-Host "5. Checking port availability..." -ForegroundColor Yellow

$ports = @(3000, 8000)
foreach ($port in $ports) {
    try {
        $connection = Test-NetConnection -ComputerName localhost -Port $port -InformationLevel Quiet -WarningAction SilentlyContinue
        if ($connection) {
            Write-Host "   ⚠️  Port $port is in use" -ForegroundColor Yellow
            Write-Host "   💡 Stop any services using port $port before deployment" -ForegroundColor Cyan
        } else {
            Write-Host "   ✅ Port $port is available" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "   ✅ Port $port is available" -ForegroundColor Green
    }
}

Write-Host ""

# Summary
Write-Host "📋 Verification Summary" -ForegroundColor Green
Write-Host "======================" -ForegroundColor Green

if ($allGood) {
    Write-Host "🎉 All checks passed! Your system is ready for container deployment." -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Yellow
    Write-Host "  1. Run: .\test-containers.ps1" -ForegroundColor Cyan
    Write-Host "  2. Or run: .\deploy.ps1" -ForegroundColor Cyan
    Write-Host "  3. Or run: docker-compose up --build -d" -ForegroundColor Cyan
} else {
    Write-Host "⚠️  Some issues need to be resolved before deployment." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please address the issues above and run this script again." -ForegroundColor Cyan
}

Write-Host ""
Write-Host "📚 Available documentation:" -ForegroundColor Yellow
Write-Host "  - DOCKER_INSTALLATION.md - Docker installation guide" -ForegroundColor Cyan
Write-Host "  - DOCKER_README.md - Docker deployment guide" -ForegroundColor Cyan
Write-Host "  - README.md - Main project documentation" -ForegroundColor Cyan
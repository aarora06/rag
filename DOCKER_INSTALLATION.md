# Docker Installation Guide for Windows

## Installing Docker Desktop

### Prerequisites
- Windows 10 64-bit: Pro, Enterprise, or Education (Build 16299 or later)
- Windows 11 64-bit: Home or Pro version 21H2 or higher
- WSL 2 feature enabled on Windows
- Virtualization enabled in BIOS

### Step 1: Enable WSL 2 (Windows Subsystem for Linux)

1. **Open PowerShell as Administrator** and run:
   ```powershell
   dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
   dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
   ```

2. **Restart your computer**

3. **Download and install the WSL2 Linux kernel update package**:
   - Download from: https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi
   - Run the installer

4. **Set WSL 2 as default version**:
   ```powershell
   wsl --set-default-version 2
   ```

### Step 2: Install Docker Desktop

#### Option 1: Using Winget (Recommended)
```powershell
winget install Docker.DockerDesktop
```

#### Option 2: Manual Download
1. Go to https://www.docker.com/products/docker-desktop/
2. Click "Download for Windows"
3. Run the installer (Docker Desktop Installer.exe)
4. Follow the installation wizard
5. Ensure "Use WSL 2 instead of Hyper-V" is checked

### Step 3: Start Docker Desktop

1. **Launch Docker Desktop** from the Start menu
2. **Accept the service agreement**
3. **Wait for Docker to start** (you'll see the Docker icon in the system tray)
4. **Verify installation** by opening PowerShell and running:
   ```powershell
   docker --version
   docker-compose --version
   ```

### Step 4: Configure Docker (Optional)

1. **Right-click Docker icon** in system tray → Settings
2. **Resources**: Adjust CPU and Memory allocation if needed
3. **General**: Ensure "Use WSL 2 based engine" is checked

## Alternative: Using Chocolatey

If you have Chocolatey installed:
```powershell
choco install docker-desktop
```

## Troubleshooting

### Common Issues

1. **"Docker Desktop requires Windows 10 Pro/Enterprise"**
   - Solution: Enable WSL 2 and use WSL 2 backend instead of Hyper-V

2. **"WSL 2 installation is incomplete"**
   - Solution: Install WSL 2 kernel update package manually

3. **"Virtualization not enabled"**
   - Solution: Enable virtualization in BIOS/UEFI settings

4. **Docker daemon not starting**
   - Solution: Restart Docker Desktop or restart computer

### Verification Commands

After installation, verify Docker is working:
```powershell
# Check Docker version
docker --version

# Check Docker Compose version
docker-compose --version

# Test Docker with hello-world
docker run hello-world

# Check Docker system info
docker system info
```

## Next Steps

Once Docker is installed and running:

1. **Navigate to the project directory**:
   ```powershell
   cd "c:\Users\aaror\Downloads\LLMProjects\rag_implementation"
   ```

2. **Set up environment variables**:
   ```powershell
   copy .env.example .env
   # Edit .env file and add your OpenAI API key
   ```

3. **Run the deployment script**:
   ```powershell
   .\deploy.ps1
   ```

4. **Or use Docker Compose directly**:
   ```powershell
   docker-compose up --build -d
   ```

## Resources

- [Docker Desktop for Windows Documentation](https://docs.docker.com/desktop/windows/)
- [WSL 2 Installation Guide](https://docs.microsoft.com/en-us/windows/wsl/install)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## Support

If you encounter issues:
1. Check Docker Desktop logs (Settings → Troubleshoot → Show logs)
2. Restart Docker Desktop
3. Check Windows Event Viewer for system errors
4. Visit Docker Community Forums or Stack Overflow
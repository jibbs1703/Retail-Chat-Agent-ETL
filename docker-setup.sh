#!/bin/bash
set -e

if command -v docker &> /dev/null; then
    echo "Docker is already installed"
    docker_version=$(docker --version)
    echo "Version: $docker_version"
    echo ""
else
    echo "Docker is not installed. Installing Docker"
    echo ""
    
    # Update package manager
    echo "Step 1: Updating package manager..."
    sudo apt-get update
    echo "Package manager updated"
    echo ""
    
    # Install Docker
    echo "Step 2: Installing Docker"
    sudo apt-get install -y docker.io
    echo "Docker installed successfully"
    echo ""
    
    # Verify installation
    docker_version=$(docker --version)
    echo " Version: $docker_version"
    echo ""
fi

echo "Step 3: Checking Docker daemon status..."
if systemctl is-active --quiet docker; then
    echo "Docker daemon is already running"
    echo ""
else
    echo "Docker daemon is not running. Starting Docker daemon..."
    sudo systemctl start docker
    echo "Docker daemon started"
    echo ""
    
    echo "Step 4: Enabling Docker to start on boot..."
    sudo systemctl enable docker
    echo "Docker enabled for auto-start on boot"
    echo ""
fi

# Add current user to docker group (optional but recommended)
echo "Step 5: Configuring user permissions..."
if id -nG "$USER" | grep -qw "docker"; then
    echo "Current user is already in docker group"
else
    echo "Adding current user to docker group..."
    sudo usermod -aG docker "$USER"
    echo "User added to docker group"
    echo "  Note: You may need to log out and log back in for group changes to take effect"
fi

# Check if Docker Compose is already installed
echo ""
echo "Step 6: Checking Docker Compose..."
if command -v docker-compose &> /dev/null; then
    echo "Docker Compose is already installed"
    compose_version=$(docker-compose --version)
    echo "  Version: $compose_version"
    echo ""
else
    echo "Docker Compose is not installed. Installing Docker Compose..."
    
    # Check if curl is installed, if not install it
    if ! command -v curl &> /dev/null; then
        echo "curl is not installed. Installing curl..."
        sudo apt-get install -y curl
        echo "curl installed successfully"
    fi
    
    # Download and install Docker Compose
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Verify installation
    compose_version=$(docker-compose --version)
    echo "Docker Compose installed successfully"
    echo "  Version: $compose_version"
    echo ""
fi

echo "Running Docker test..."
docker run --rm hello-world

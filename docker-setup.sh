#!/bin/bash
set -e

if command -v docker &> /dev/null; then
    docker_version=$(docker --version)
    echo "Version: $docker_version"
else
    sudo apt-get update
    sudo apt-get install -y docker.io
    docker_version=$(docker --version)
    echo " Version: $docker_version"
fi

if systemctl is-active --quiet docker; then
else
    sudo systemctl start docker
    sudo systemctl enable docker
fi

if id -nG "$USER" | grep -qw "docker"; then
else
    sudo usermod -aG docker "$USER"
fi

if command -v docker-compose &> /dev/null; then
    compose_version=$(docker-compose --version)
    echo "  Version: $compose_version"
else    
    if ! command -v curl &> /dev/null; then
        sudo apt-get install -y curl
    fi
    sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    sudo chmod +x /usr/local/bin/docker-compose
    compose_version=$(docker-compose --version)
    echo "  Version: $compose_version"
fi

echo "Running Docker test..."
sudo docker run --rm hello-world

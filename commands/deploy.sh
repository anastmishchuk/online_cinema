#!/bin/bash

# Exit the script immediately if any command exits with a non-zero status
set -e

# Function to handle errors with custom messages
handle_error() {
    echo "Error: $1"
    exit 1
}

# Navigate to the application directory
cd /home/ubuntu/src/online_cinema || handle_error "Failed to navigate to the application directory."

# Fetch the latest changes from the remote repository
echo "Fetching the latest changes from the remote repository..."
git fetch origin deploy || handle_error "Failed to fetch updates from the 'origin' remote."

# Reset the local repository to match the remote 'deploy' branch
echo "Resetting the local repository to match 'origin/deploy'..."
git reset --hard origin/deploy || handle_error "Failed to reset the local repository to 'origin/deploy'."

# (Optional) Pull any new tags from the remote repository
echo "Fetching tags from the remote repository..."
git fetch origin --tags || handle_error "Failed to fetch tags from the 'origin' remote."

# Build and run Docker containers with Docker Compose v2
docker compose -f docker-compose.yml up -d --build || handle_error "Failed to build and run Docker containers using docker-compose.yml."

# Print a success message upon successful deployment
echo "Deployment completed successfully."

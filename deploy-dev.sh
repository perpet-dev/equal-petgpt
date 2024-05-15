#!/bin/bash

# Enable error handling
set -e

# Variable settings
REGISTRY="dev.promptinsight.ai"
REPO_NAME="dev/petgpt-service"
REGISTRY_REPO="${REGISTRY}/${REPO_NAME}"

# Prompt the user for project version
read -p "Please enter the project version: " IMAGE_TAG
if [ -z "$IMAGE_TAG" ]; then
    echo "Error: No version input provided. Exiting..."
    exit 1
fi

# Build Docker image
docker build --no-cache -t ${REGISTRY_REPO} .

# Tag and push the image to the repository
docker tag ${REGISTRY_REPO}:latest ${REGISTRY_REPO}:${IMAGE_TAG}
docker push ${REGISTRY_REPO}:${IMAGE_TAG}
docker push ${REGISTRY_REPO}:latest

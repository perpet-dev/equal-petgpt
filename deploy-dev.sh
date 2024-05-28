#!/bin/bash

# Enable error handling
set -e

# Variable settings
REGISTRY="dev.promptinsight.ai"
REPO_NAME="dev/petgpt-service"
REGISTRY_REPO="${REGISTRY}/${REPO_NAME}"

# Prompt the user for project version
# Prompt user for project version
read -p "Please enter the project version (default is 'latest'): " IMAGE_TAG
IMAGE_TAG=${IMAGE_TAG:-latest}

# Build and push Docker image with inline cache
docker buildx build --platform linux/amd64 \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --cache-from=type=registry,ref="${REGISTRY_REPO}:latest" \
  -t "${REGISTRY_REPO}:${IMAGE_TAG}" \
  -t "${REGISTRY_REPO}:latest" \
  --push .

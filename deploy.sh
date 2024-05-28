#!/bin/bash
# Enable error handling
set -e

# Set variables
REGION="ap-northeast-2"
ACCOUNT_ID="868615245439"
REPO_NAME="equal/petgpt-service"
ECR="${ACCOUNT_ID}.dkr.ecr.${REGION}.amazonaws.com"
REGISTRY_REPO="${ECR}/${REPO_NAME}"

# Prompt user for project version
read -p "Please enter the project version (default is 'latest'): " IMAGE_TAG
IMAGE_TAG=${IMAGE_TAG:-latest}

# ECR login
PASSWORD=$(aws ecr get-login-password --region "${REGION}")
if [ $? -ne 0 ]; then
    echo "Failed to get ECR login password."
    exit 1
fi

echo "${PASSWORD}" | docker login --username AWS --password-stdin "${ECR}"
if [ $? -ne 0 ]; then
    echo "Failed to login to ECR."
    exit 1
fi

# Build and push Docker image with inline cache
docker buildx build --platform linux/amd64 \
  --build-arg BUILDKIT_INLINE_CACHE=1 \
  --cache-from=type=registry,ref="${REGISTRY_REPO}:latest" \
  -t "${REGISTRY_REPO}:${IMAGE_TAG}" \
  -t "${REGISTRY_REPO}:latest" \
  --push .

# Check if the build was successful
if [ $? -ne 0 ]; then
    echo "Docker build and push failed."
    exit 1
fi

echo "Docker images have been successfully built and pushed."

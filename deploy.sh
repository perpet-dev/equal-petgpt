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
echo "${PASSWORD}" | docker login --username AWS --password-stdin "${ECR}"

# Build and push Docker image for multiple platforms
if [ "${IMAGE_TAG}" != "latest" ]; then
    docker buildx build --platform linux/amd64,linux/arm64 --no-cache -t "${REGISTRY_REPO}:${IMAGE_TAG}" --push .
fi

docker buildx build --platform linux/amd64,linux/arm64 --no-cache -t "${REGISTRY_REPO}:latest" --push .

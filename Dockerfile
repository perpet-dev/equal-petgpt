# Use an official Python runtime as a parent image
#FROM python:3.8-slim
FROM python:3.9-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psutil and other packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev netcat-openbsd && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt initially
COPY requirements.txt .
RUN pip install -r requirements.txt
# Copy the current directory contents into the container at /app
COPY . .
# # Copy entrypoint script
# COPY entrypoint.sh /app/entrypoint.sh
# # Make the entrypoint script executable
# RUN chmod +x /app/entrypoint.sh
# # Make port available to the world outside this container
# # Copy the Eureka registration script
# COPY register_with_eureka.py /app/register_with_eureka.py

ENV PORT 10070

# Expose the port the app runs on
EXPOSE $PORT

CMD uvicorn server:app --host 0.0.0.0 --port $PORT --workers 4
# ENTRYPOINT ["/app/entrypoint.sh"]
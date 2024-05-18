# Use an official Python runtime as a parent image
FROM python:3.8-slim

# Set the working directory in the container
WORKDIR /app

# Install system dependencies required for psutil and other packages
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy only the requirements.txt initially
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
#RUN pip install --no-cache-dir -r requirements.txt
RUN pip install -r requirements.txt
# Copy the current directory contents into the container at /app
COPY . .

# Make port 80 available to the world outside this container
EXPOSE 10070

# Define environment variable
ENV PORT 10070

# CMD can still use variable substitution in the shell form
#CMD ["python", "server.py"]
#CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", $PORT, "--workers", "4"]
CMD uvicorn server:app --host 0.0.0.0 --port $PORT --workers 5 --limit-concurrency 100 --timeout-keep-alive 5
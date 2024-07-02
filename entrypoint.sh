#!/bin/sh
set -e

# Function to check if a port is available
is_port_available() {
  ! nc -z localhost $1
}

# Dynamically assign a port within the range 10070-10080
PORT=$(shuf -i 10070-10080 -n 1)
while ! is_port_available $PORT; do
  PORT=$(shuf -i 10070-10080 -n 1)
done

# Function to register with Eureka
register_with_eureka() {
    python -c "
import requests
from py_eureka_client import eureka_client
import os
import logging
import time
import socket

# Configuration variables
PORT = int(os.getenv('PORT', 10070))
EUREKA = os.getenv('EUREKA_CLIENT_SERVICEURL_DEFAULTZONE', 'http://dev.promptinsight.ai:10001/eureka')
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('eureka')

def get_ip_address():
    environment = os.getenv('ENVIRONMENT', 'dev')
    if environment == 'prod':
        return get_ec2_instance_ip()
    else:
        # Get the local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.254.254.254', 1))
            IP_ADDRESS = s.getsockname()[0]
        except Exception:
            IP_ADDRESS = '127.0.0.1'
        finally:
            s.close()
        return IP_ADDRESS

def get_ec2_instance_ip():
    try:
        token_response = requests.put(
            'http://169.254.169.254/latest/api/token',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
        )
        token_response.raise_for_status()
        token = token_response.text

        ip_response = requests.get(
            'http://169.254.169.254/latest/meta-data/local-ipv4',
            headers={'X-aws-ec2-metadata-token': token}
        )
        ip_response.raise_for_status()
        return ip_response.text
    except requests.RequestException as e:
        logger.error(f'Error fetching EC2 instance IP: {e}')
        raise

def register():
    IP_ADDRESS = get_ip_address()
    try:
        logger.debug(f'Registering with Eureka at {EUREKA}...')
        eureka_client.init(eureka_server=EUREKA,
                           app_name='petgpt-service',
                           instance_host=IP_ADDRESS,
                           instance_port=PORT,
                           renewal_interval_in_secs=30,  # Heartbeat interval
                           duration_in_secs=90)          # Duration before expiration
        logger.info(f'Registration with Eureka successful with IP: {IP_ADDRESS} and port {PORT}')
    except Exception as e:
        logger.error(f'Failed to register with Eureka: {e}')
        raise

while True:
    try:
        register()
        break
    except Exception as e:
        logger.error(f'Registration failed, retrying in 30 seconds: {e}')
        time.sleep(30)

while True:
    try:
        # Additional check to ensure registration is alive
        # For example, we can fetch the registry and check our instance
        response = requests.get(f'{EUREKA}/apps/petgpt-service')
        if response.status_code != 200:
            logger.warning('Service not registered, retrying registration...')
            register()
    except Exception as e:
        logger.error(f'Error checking registration status, retrying registration: {e}')
        register()
    time.sleep(60)  # Check every minute
"
}

# Start the registration process in the background
register_with_eureka &

# Start the FastAPI application
exec uvicorn server:app --host 0.0.0.0 --port $PORT --workers 4 --limit-concurrency 100 --timeout-keep-alive 5 --log-level info

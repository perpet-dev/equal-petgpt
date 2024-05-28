import requests
from py_eureka_client import eureka_client
import os
import logging

# Configuration variables
PORT = int(os.getenv("PORT", 10070))
#EUREKA = os.getenv("EUREKA", "http://localhost:8761/eureka")
from config import EUREKA
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("eureka")

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
        logger.error(f"Error fetching EC2 instance IP: {e}")
        raise

def register_with_eureka():
    IP_ADDRESS = get_ec2_instance_ip()
    try:
        logger.debug(f"Registering with Eureka at {EUREKA}...")
        eureka_client.init(eureka_server=EUREKA,
                           app_name="petgpt-service",
                           instance_host=IP_ADDRESS,
                           instance_port=PORT)
        logger.info(f"Registration with Eureka successful with IP: {IP_ADDRESS} and port {PORT}")
    except Exception as e:
        logger.error(f"Failed to register with Eureka: {e}")
        raise

if __name__ == "__main__":
    register_with_eureka()

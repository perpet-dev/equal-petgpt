import requests
from py_eureka_client import eureka_client
import os
import logging

# Configuration variables
EUREKA_SERVER = 'http://dev.promptinsight.ai:10001/eureka'
APP_NAME = 'backsurvey-service'#'petgpt-service'
INSTANCE_PORT = 10080  # The port of the instance you want to unregister

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('eureka')

def get_ip_address():
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't even have to be reachable
        s.connect(('10.254.254.254', 1))
        IP_ADDRESS = s.getsockname()[0]
    except Exception:
        IP_ADDRESS = '127.0.0.1'
    finally:
        s.close()
    return IP_ADDRESS

IP_ADDRESS = "192.168.0.3"

def unregister_instance():
    try:
        instance_id = "172.30.1.95:backsurvey-service:8080" # f'{IP_ADDRESS}:{APP_NAME}:{INSTANCE_PORT}'
        url = f'{EUREKA_SERVER}/apps/{APP_NAME}/{instance_id}'
        logger.debug(f'Unregistering instance {instance_id} from Eureka at {url}...')
        
        response = requests.delete(url)
        response.raise_for_status()
        
        logger.info(f'Unregistration of instance {instance_id} successful')
    except Exception as e:
        logger.error(f'Failed to unregister instance {instance_id} from Eureka: {e}')
        raise
    
unregister_instance()
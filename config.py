import os
from dotenv import load_dotenv
load_dotenv()
import logging
import logging.config
LOGGING_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
PORT = int(os.getenv('PORT', 9090))
WEBSOCKET_URL = os.getenv('WEBSOCKET_URL', "ws://dev.promptinsight.ai:10002/petgpt-service/ws/generation/")
EUREKA = os.getenv('EUREKA_CLIENT_SERVICEURL_DEFAULTZONE', "http://dev.promptinsight.ai:10001/eureka") 
PREFIXURL= os.getenv('PREFIXURL', "/petgpt-service")

OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_ORG = os.getenv('OPENAI_ORG', "org-oMDD9ptBReP4GSSW5lMD1wv6")
OPENAI_PROJ = os.getenv('OPENAI_PROJ', "proj_cfKAM38EYeptw1DVgvQ1K3xm")
GPT4VISIOMMODEL = os.getenv('GPT4VISIOMMODEL', "gpt-4-turbo") #gpt-4-vision-preview
GPT4DEFAULT = os.getenv('GPT4DEFAULT', "gpt-4-turbo") #gpt-4-turbo
OPENAI_EMBEDDING_MODEL_NAME = 'text-embedding-3-small'
OPENAI_EMBEDDING_DIMENSION = 1536
PINECONE_INDEX =  'equalapp-240514'  
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')

# Set pymongo's OCSP support logger to INFO level
ocsp_logger = logging.getLogger('pymongo.ocsp_support')
ocsp_logger.setLevel(logging.INFO)

# MongoDB connection string
# MONGODB = "mongodb+srv://ivanberlocher:P4XZZRTkgbG6iRcX@perpet.uhcs1fw.mongodb.net/?retryWrites=true&w=majority"
#MONGODB = "mongodb+srv://ivanberlocher:P4XZZRTkgbG6iRcX@perpet.uhcs1fw.mongodb.net/?retryWrites=true&w=majority"
MONGODB = os.getenv('MONGODB', "mongodb+srv://perpetcloud:NsIgvcQ5E7OQ2JSW@equalpet.tt45urw.mongodb.net/") 
#MariaDB connection info
DB_URI = os.getenv('DB_URI', "jdbc:mariadb://dev.promptinsight.ai:3306/perpet?allowPublicKeyRetrieval=true&useSSL=false&serverTimezone=Asia/Seoul")
DB_HOST = os.getenv('DB_HOST', 'dev.promptinsight.ai') #"dev.promptinsight.ai" # "127.0.0.1" # 
DB_USER = os.getenv('DB_USER', 'perpetdev') #"perpetdev" # "perpetapi" # 
DB_PASSWORD = os.getenv('DB_PASSWORD', "perpet1234!") #"perpet1234!" # "O7dOQFXQ1PYY" # 
DB_DATABASE = os.getenv('DB_DATABASE', 'perpet')
DB_PORT = int(os.getenv('DB_PORT', 3306))
#For production rdbs
#DB_URI=mysql+aiomysql://perpetapi:O7dOQFXQ1PYY@prod-perpet.coxtlbkqbiqx.ap-northeast-2.rds.amazonaws.com:3306/perpet?charset=utf8mb4 
#DB_HOST="prod-perpet.coxtlbkqbiqx.ap-northeast-2.rds.amazonaws.com"
#DB_USER="perpetapi"
#DB_PASSWORD="O7dOQFXQ1PYY"
#DB_DATABASE="perpet"
#DB_PORT=3306
LOG_NAME = 'EqualPetGPT'
LOG_FILE_NAME = './log/petgpt.log'
USE_SALES_PROMPT = True
EQUALAPIURL = os.getenv('EQUALAPIURL', "https://api2.equal.pet")

import socket
HOSTNAME = socket.gethostname()
IP_ADDRESS = socket.gethostbyname(HOSTNAME)
# Define the fetch URL for sending notifications
FETCH_URL_NOTIF = "https://api2.equal.pet/petgpt-service/send-notification"

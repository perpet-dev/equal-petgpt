import os
import logging
import logging.config
LOGGING_LEVEL = os.getenv('LOG_LEVEL', 'DEBUG')
PORT = int(os.getenv('PORT', 9090))
EUREKA = os.getenv('EUREKA_CLIENT_SERVICEURL_DEFAULTZONE', "http://dev.promptinsight.ai:10001/eureka") 
#EUREKA = os.getenv('EUREKA_CLIENT_SERVICEURL_DEFAULTZONE', "http://43.203.217.43:10001/eureka") 
PREFIXURL="/petgpt-service"
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_ORG = "org-oMDD9ptBReP4GSSW5lMD1wv6"
OPENAI_PROJ = "proj_cfKAM38EYeptw1DVgvQ1K3xm"
#OPENAI_API_KEY = "sk-proj-0CpN18GYzMl614IG7TonT3BlbkFJmAkkvleEPkZ3hqP1K24E"
OPENAI_API_KEY = "sk-proj-IflClp49epIOSBVKlmcrT3BlbkFJNWifAmYTHOqV6Tw2wJjL"

OPENAI_EMBEDDING_MODEL_NAME = 'text-embedding-3-small'
OPENAI_EMBEDDING_DIMENSION = 1536
PINECONE_API_KEY =  'dcce7d00-5f7f-48bf-8b19-33480e74ad12'
PINECONE_INDEX =  'test-index-0325'

# Set pymongo's OCSP support logger to INFO level
ocsp_logger = logging.getLogger('pymongo.ocsp_support')
ocsp_logger.setLevel(logging.INFO)

# MongoDB connection string
# MONGODB = "mongodb+srv://ivanberlocher:P4XZZRTkgbG6iRcX@perpet.uhcs1fw.mongodb.net/?retryWrites=true&w=majority"
#MONGODB = "mongodb+srv://ivanberlocher:P4XZZRTkgbG6iRcX@perpet.uhcs1fw.mongodb.net/?retryWrites=true&w=majority"
MONGODB = "mongodb+srv://perpetcloud:NsIgvcQ5E7OQ2JSW@equalpet.tt45urw.mongodb.net/"
#MariaDB connection info
DB_URI = os.getenv('DB_URI', "jdbc:mariadb://dev.promptinsight.ai:3306/perpet?allowPublicKeyRetrieval=true&useSSL=false&serverTimezone=Asia/Seoul")
DB_HOST = "dev.promptinsight.ai" # "127.0.0.1" # 
DB_USER = "perpetdev" # "perpetapi" # 
DB_PASSWORD = "perpet1234!" # "O7dOQFXQ1PYY" # 
DB_DATABASE = "perpet"
DB_PORT = 3306 # 3307

LOG_NAME = 'EqualPetGPT'
LOG_FILE_NAME = './log/petgpt.log'
USE_SALES_PROMPT = True




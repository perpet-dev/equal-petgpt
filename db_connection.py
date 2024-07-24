import mysql.connector
from mysql.connector import pooling
import time
from mysql.connector import Error
import logging
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE

logger = logging.getLogger(__name__)

# # Create a connection pool
# try:
#     connection_pool = mysql.connector.pooling.MySQLConnectionPool(
#         pool_name="mypool",
#         pool_size=5,  # Adjust pool size as needed
#         pool_reset_session=True,
#         host=DB_HOST,
#         database=DB_DATABASE,
#         user=DB_USER,
#         password=DB_PASSWORD,
#         port=DB_PORT,
#         charset='utf8mb4',
#         collation='utf8mb4_general_ci'
#     )
#     logger.info("Connection pool created successfully.")
# except Error as e:
#     logger.error(f"Error creating connection pool: {e}")
#     connection_pool = None

# Retry configuration
MAX_RETRIES = 5
RETRY_DELAY = 5  # in seconds

def create_connection_pool():
    retries = 0
    connection_pool = None

    while retries < MAX_RETRIES:
        try:
            connection_pool = mysql.connector.pooling.MySQLConnectionPool(
                pool_name="mypool",
                pool_size=5,  # Adjust pool size as needed
                pool_reset_session=True,
                host=DB_HOST,
                database=DB_DATABASE,
                user=DB_USER,
                password=DB_PASSWORD,
                port=DB_PORT,
                charset='utf8mb4',
                collation='utf8mb4_general_ci'
            )
            logger.info("Connection pool created successfully.")
            break  # Exit the loop if the connection pool is created successfully
        except Error as e:
            retries += 1
            logger.error(f"Error creating connection pool: {e}")
            if retries < MAX_RETRIES:
                logger.info(f"Retrying to create connection pool in {RETRY_DELAY} seconds... (Attempt {retries}/{MAX_RETRIES})")
                time.sleep(RETRY_DELAY)
            else:
                logger.error("Max retries reached. Failed to create connection pool.")
                break

    return connection_pool

# Create the connection pool
connection_pool = create_connection_pool()

def get_connection():
    try:
        if connection_pool:
            connection = connection_pool.get_connection()
            logger.info("Successfully obtained connection from pool.")
            return connection
        else:
            logger.error("Connection pool is not available.")
            return None
    except Error as e:
        logger.error(f"Error getting connection from pool: {e}")
        return None

def close_connection(connection):
    if connection:
        try:
            # Check if connection is not None and is connected
            if connection and hasattr(connection, 'is_connected') and connection.is_connected():
                connection.close()
                logger.debug("Connection returned to pool.")
            else:
                logger.warning("Connection is None or not connected, cannot return to pool.")
        except AttributeError as e:
            logger.error(f"AttributeError returning connection to pool: {e}")
        except Error as e:
            logger.error(f"Error closing connection: {e}")
    else:
        logger.warning("Connection is None, nothing to close.")

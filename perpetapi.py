# Path: perpetapi.py
import requests
from config import LOG_FILE_NAME, LOGGING_LEVEL, LOG_NAME, EQUALAPIURL
from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)

def login(user_id, channel_type):
    # The URL to which the request is sent
    url = f"{EQUALAPIURL}/user-service/v1/auth/social"

    # The JSON data you want to send with the request
    data = {
        "id": f"{user_id}",
        "type": f"{channel_type}"
    }

    # Sending a POST request
    response = requests.post(url, json=data)

    # Checking if the request was successful
    if response.status_code == 200:
        # Parsing the JSON response
        json_response = response.json()
        logger.debug("Login Successful:", json_response)
        return {
            "accessToken": json_response["data"]["accessToken"],
            "user_id": json_response["data"]["id"],
            "signUp": json_response["data"]["signUp"],
            "refreshToken": json_response["data"]["refreshToken"]
        }
    else:
        logger.error("Login Failed:", response.status_code)
        return {
            "success": False,
            "message": "Login failed"
        }
    
def getPetInfoList(access_token):
    # Endpoint for the GET request
    endpoint = f"{EQUALAPIURL}/user-service/v1/pet/list"
    # Headers including the Authorization header with the Bearer token
    headers = {
        "Authorization": f"Bearer {access_token}"
    }
    # Parameters for the GET request
    params = {
        "page": 0,
        "limit": "",  # Specify limit if needed
        "type": "",   # Specify type if needed
        "name": "",   # Specify name if needed
        "main_yn": "" # Specify main_yn if needed (e.g., "Y" or "N")
    }

    # Sending a GET request
    response = requests.get(url=f"{endpoint}", params=params, headers=headers)

    # Checking if the request was successful
    if response.status_code == 200:
        # Parsing the JSON response
        json_response = response.json()
        logger.debug("Request Successful:", json_response)
    else:
        logger.error("Request Failed:", response.status_code)
        # Checking if the request was successful

# Example usage
# user_id = "001539.a6d68bcd08e24b40bd2fcd25832e8ab9.0344"
# channel_type = "APPLE"

# channel_type = "KAKAO"
# user_id = "3058651892"

# login_details = login(user_id, channel_type)
# if login_details:
#     getPetInfoList(login_details["accessToken"])


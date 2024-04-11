# Path: perpetapi.py
import requests
# The base URL or proxy-client where your service is hosted
base_url =  "https://api.equal.pet"

def login(user_id, channel_type):
    # The URL to which the request is sent
    url = f"{base_url}/user-service/v1/auth/social"

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
        print("Login Successful:", json_response)
        return {
            "accessToken": json_response["data"]["accessToken"],
            "user_id": json_response["data"]["id"],
            "signUp": json_response["data"]["signUp"],
            "refreshToken": json_response["data"]["refreshToken"]
        }
    else:
        print("Login Failed:", response.status_code)
        return {
            "success": False,
            "message": "Login failed"
        }
    
def getPetInfoList(access_token):
    # Endpoint for the GET request
    endpoint = f"{base_url}/user-service/v1/pet/list"
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
        print("Request Successful:", json_response)
    else:
        print("Request Failed:", response.status_code)
        # Checking if the request was successful

# Example usage
# user_id = "001539.a6d68bcd08e24b40bd2fcd25832e8ab9.0344"
# channel_type = "APPLE"

channel_type = "KAKAO"
user_id = "3058651892"

login_details = login(user_id, channel_type)
if login_details:
    getPetInfoList(login_details["accessToken"])


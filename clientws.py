import websocket
import json
import threading

from config import LOG_FILE_NAME, LOGGING_LEVEL, LOG_NAME
from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)

from petprofile import PetProfileRetriever
petProfileRetriever = PetProfileRetriever()

def on_message(ws, pet_id, message):
    #print("on_message\n")
    global accumulated_message
    data = json.loads(message) 
    pet_profile = petProfileRetriever.get_pet_profile(pet_id)
    pet_type = pet_profile.pet_type # 고양이 . 강아지
    pet_name = pet_profile.pet_name # 이름
    pet_age = pet_profile.age # 나이
    pet_tag_id = pet_profile.tag_id # 태그
    pet_breed = pet_profile.breed # 견종, 묘종
    pet_weight = "{}kg".format(pet_profile.weight) # 몸무게
    
    # Parse the incoming message string to a dictionary
    if 'content' in data:
        # Append the new message to the accumulated messages
        content = json.loads(f'"{data["content"]}"') 
        accumulated_message +=  content# Unescape using json.loads
        print(f"Received message: {content}")
    if 'finished' in data and data['finished']:
        print("Final accumulated message:", accumulated_message)
        ws.close()  # Close the websocket after receiving the final message


def on_error(ws, error):
    print(f"Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("### closed ###")

def on_open(ws):
    print("WebSocket opened")

    def run(*args):
        # Construct the message you want to send
        data = {
            "messages": [
                {
                    "role": "user",
                    "content": "고양이의 우울증에 도움이 되는 영양보충제가 있을까요?"
                }
            ]
        }
        ws.send(json.dumps(data))
        print("Message sent")

    thread = threading.Thread(target=run)
    thread.start()
accumulated_message = ""  # Initialize an empty string to accumulate messages

if __name__ == "__main__":
    websocket.enableTrace(True)
    wsurl = "ws://dev.promptinsight.ai:10002/petgpt-service/ws/generation"
    #wsurl = "ws://localhost:10000/ws/generation"
    ws = websocket.WebSocketApp(wsurl,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)
    ws.run_forever()
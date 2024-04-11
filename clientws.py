import websocket
import json
import threading

def on_message(ws, message):
    global accumulated_message
    data = json.loads(message)  # Parse the incoming message string to a dictionary
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
    #"ws://localhost:9090/ws/generation"
    ws = websocket.WebSocketApp(wsurl,
                                on_open=on_open,
                                on_message=on_message,
                                on_error=on_error,
                                on_close=on_close)

    ws.run_forever()


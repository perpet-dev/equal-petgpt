import httpx
import asyncio
import json
import random 
from pymongo import MongoClient
import datetime


from typing import List
import aiohttp
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from petprofile import PetProfileRetriever

from config import LOG_NAME, LOGGING_LEVEL, LOG_FILE_NAME

from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)
from petprofile import PetProfileRetriever
from config import OPENAI_API_KEY, API_URL, MONGODB


client = MongoClient(MONGODB)
mongo_db = client.perpet_healthcheck
petgpt_collection = mongo_db["petgpt_logs"]

USE_SALES_PROMPT = True
sales_prompt = " Also you should recommend '이퀄 영양제' for pet's health like salesman. '이퀄 영양제' has '품종별 영양제' for '말티즈','푸들', '리트리버', '포메라니안', '코리안숏헤어', '골든리트리버' and '1:1 맞춤 영양제' for all breeds"

system_with_image = "You are 'PetGPT', a friendly and enthusiastic GPT that specializes in analyzing images of dogs and cats. \
    Upon receiving an image, you identifies the pet's breed, age and weight. PetGPT provides detailed care tips, \
    including dietary recommendations, exercise needs, and general wellness advice, emphasizing suitable vitamins and supplements. \
    PetGPT, as an AI tool, is exceptionally equipped to assist pet owners with a wide range of questions and challenges. \
    It can provide immediate, accurate, and tailored advice on various aspects of pet care, including health, behavior, \
    nutrition, grooming, exercise, and general well-being. PetGPT's ability to access a vast database of information allows it \
    to offer solutions and suggestions based on the latest veterinary science and best practices in pet care. \
    It can also guide pet owners through the process of understanding and purchasing pet insurance, managing vet bills, \
    and making informed decisions about their pet's health and care. \
    Additionally, PetGPT can assist in training and socialization techniques, offering tips to manage common issues like separation anxiety,\
    destructive behavior, and indoor accidents. Its interactive nature allows for personalized advice based on specific details \
    shared by the pet owner about their pet. Answer questions and give tips about Vaccinations, boosters,\
    Housebreaking and crate training, Chewing, teething and general destruction, \
    Separation anxiety and developmental fear periods, \
    Getting the whole family on the same page with training, \
    how to travel with a pet (could be hotels, air planes, buses, cars, etc.). \
    Answer in the same language as the question."
system_txt = "You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare for dogs and cats to assist pet owners with a wide range of questions and challenges. \
    PetGPT provides detailed care tips, including dietary recommendations, exercise needs, and general wellness advice, emphasizing suitable vitamins and supplements. \
    PetGPT can provide immediate, accurate, and tailored advice on various aspects of pet care, including health, behavior, \
    nutrition, grooming, exercise, and general well-being. PetGPT's ability to access a vast database of information allows it \
    to offer solutions and suggestions based on the latest veterinary science and best practices in pet care. \
    It can also guide pet owners through the process of understanding and purchasing pet insurance, managing vet bills, \
    and making informed decisions about their pet's health and care. \
    Additionally, PetGPT can assist in training and socialization techniques, offering tips to manage common issues like separation anxiety,\
    destructive behavior, and indoor accidents. Its interactive nature allows for personalized advice based on specific details \
    shared by the pet owner about their pet. Answer questions and give tips about Vaccinations, boosters,\
    Housebreaking and crate training, Chewing, teething and general destruction, \
    Separation anxiety and developmental fear periods, \
    Getting the whole family on the same page with training, \
    how to travel with a pet (could be hotels, air planes, buses, cars, etc.). \
    Answer in the same language as the question. Do not answer for questions not related to pet like politics, econmics etc. \
    Also provide a response without paragraph break. \
    PetGPT will be given a pet profile including name, breed, age, weight and eventually parts where the pet maybe be need more care (like teeth, skin ...). \
    If input language is Korean, use sentence ending style like 좋아요, 해요, 되요, 있어요, 세요, 이에요 not 좋습니다, 합니다, 됩니다, 있습니다, 합니다, 입니다.  \
    And use emoji, emoticons if possible."

# Assuming API key and custom model/server configurations are set elsewhere
# openai.api_key = "your-api-key"
# openai.api_base = "your-api-base-url"

def save_to_petgpt_log(pet_id : int, question: str, answer: str):
    """ Saves or updates image data along with user and pet information in MongoDB """
    try:
        # Define the filter for the document to find it if it already exists
        #filter = {"user_id": user_id, "pet_idname": pet_name}

        # Define the update to apply
        update = {
            "pet_id":pet_id,
            "question":question,
            "answer":answer,
            "time_stamp": datetime.now()
        }

        petgpt_collection.insert_one(update)

    except Exception as e:
        logger.error(f"An error occurred: {e}")
       
# Example of filtering out unsupported fields from messages before sending to OpenAI
def prepare_messages_for_openai(messages):
    logger.debug('prepare_messages_for_openai')
    # Define the allowed fields in a message
    allowed_fields = {'role', 'content'}

    # Filter each message to only include allowed fields
    filtered_messages = []
    for message in messages:
        filtered_message = {key: value for key, value in message.items() if key in allowed_fields}
        filtered_messages.append(filtered_message)
    return filtered_messages

import openai
from openai import OpenAI
async def handle_text_messages(websocket: WebSocket, model, conversation, pet_id):
    logger.debug('handle_text_messages')
    logger.debug('pet_id: {} , conversation: {}'.format(pet_id, conversation))

    system = "You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare for dogs and cats to assist pet owners with a wide range of questions and challenges. \
            PetGPT provides detailed care tips, including dietary recommendations, exercise needs, and general wellness advice, emphasizing suitable vitamins and supplements. \
            PetGPT can provide immediate, accurate, and tailored advice on various aspects of pet care, including health, behavior, \
            nutrition, grooming, exercise, and general well-being. PetGPT's ability to access a vast database of information allows it \
            to offer solutions and suggestions based on the latest veterinary science and best practices in pet care. \
            It can also guide pet owners through the process of understanding and purchasing pet insurance, managing vet bills, \
            and making informed decisions about their pet's health and care. \
            Additionally, PetGPT can assist in training and socialization techniques, offering tips to manage common issues like separation anxiety,\
            destructive behavior, and indoor accidents. Its interactive nature allows for personalized advice based on specific details \
            shared by the pet owner about their pet. Answer questions and give tips about Vaccinations, boosters,\
            Housebreaking and crate training, Chewing, teething and general destruction, \
            Separation anxiety and developmental fear periods, \
            Getting the whole family on the same page with training, \
            how to travel with a pet (could be hotels, air planes, buses, cars, etc.). \
            Answer in the same language as the question. Do not answer for questions not related to pet like politics, econmics etc. \
            Also provide a response without paragraph break. \
            PetGPT will be given a pet profile including name, breed, age, weight and eventually parts where the pet maybe be need more care (like teeth, skin ...). \
            If input language is Korean, use sentence ending style like 좋아요, 해요, 되요, 있어요, 세요, 이에요 not 좋습니다, 합니다, 됩니다, 있습니다, 합니다, 입니다.  \
            And use emoji, emoticons if possible."

    retriever = PetProfileRetriever()
    pet_profile = retriever.get_pet_profile(pet_id)
    retriever.close()
        
    logger.info(f"handle_text_messages for Pet profile: {pet_profile}")
    
    # if 'error' in pet_profile:
    #     system_message = {"role": "system", "content": system}
    # else:
    system_message = construct_system_message(pet_profile, system)
        
        # pet_info_prompt = "pet name: {}, breed: {}, age: {}, weight: {}kg".format(pet_profile.pet_name, pet_profile.breed, pet_profile.age, pet_profile.weight)
        # logger.debug(pet_info_prompt)
        # system_prompt = system + "\n You are assisting " + pet_info_prompt 
        # system_message = {"role": "system", "content": system_prompt}                
        
    conversation_with_system = [system_message] + conversation
    query = conversation
    #message_stream_id = str(uuid.uuid4())
    conversation = prepare_messages_for_openai(conversation_with_system)
    await send_message_to_openai(model, pet_id, query, conversation, websocket)
    
async def send_message_to_openai(model, pet_id, query, conversation, websocket):
    logger.debug('send_message_to_openai')
    message_tot = ''
    # Synchronously call the OpenAI API without await
    client = OpenAI(
        organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
        api_key=OPENAI_API_KEY
    )
    response = client.chat.completions.create(
        model = model,
        messages=conversation,
        temperature=0,
        max_tokens=1024,
        stream=True
    )
    message_stream_id = str(uuid.uuid4())
    # iterate through the stream of events
    try:
        logger.debug("Generation WebSocket to ChatGPT.")
        for chunk in response:
            chunk_message = chunk.choices[0].delta.content  # extract the message
            if  chunk_message is not None:
                chunk_message_with_id = {"id": message_stream_id, "content":chunk_message}
                #send to socket
                #logger.info(f"Generation WebSocket to ChatGPT {chunk_message_with_id}")
                message_tot = message_tot + chunk_message.replace('\n', ' ')
                await websocket.send_json(chunk_message_with_id)
        # Send a finished signal with the same ID
        if len(query) > 0 and 'content' in query[0]:
            logger.info("PETGPT_LOG: {{ pet_id: {}, message_id: {}, query: \"{}\", answer: \"{}\" }}".format(pet_id, message_stream_id, query[0]['content'], message_tot))
            save_to_petgpt_log(pet_id, query[0]['content'], message_tot)
        await websocket.send_json({"id": message_stream_id, "finished": True})

    except Exception as e:
        logger.error(f"Error processing text message: {e}", exc_info=True)
        await websocket.send_json({"error": "Error processing your request"})

async def handle_image_messages(websocket: WebSocket, model, messages):
    logger.debug('handle_image_messages')
    try:
        client = OpenAI(
            organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
            api_key=OPENAI_API_KEY
        )
        response = client.chat.completions.create(
            model = model,#"gpt-4-vision-preview"{}
            messages=[
                    {"role": "system", "content": system},
                    {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "What’s in this image?"},
                        {
                        "type": "image_url",
                        "image_url": {
                            "url": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
                        },
                        },
                    ],
                    }
                ],
                max_tokens=4096,
        )

        print(response.choices[0])

        choice = response.choices[0]
        message = choice.message

        # Manually create the response dictionary
        answer = {
            "finish_reason": choice.finish_reason,
            "index": choice.index,
            "logprobs": choice.logprobs,
            "content": message.content,
            "role": message.role,
            "function_call": message.function_call,
            "tool_calls": message.tool_calls,
            "finished": True  # Add 'finished': true to the response
        }

        logger.info(answer)
        await websocket.send_json(answer)
    except Exception as e:
        logger.error(f"Error processing text message: {e}", exc_info=True)
        await websocket.send_json({"error": "Error processing your request"})


async def openai_chat_api_request(model: str, messages: List[dict]):
    logger.debug('openai_chat_api_request')
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model,
        "messages": messages
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(API_URL, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"OpenAI API error: {response.status}")
                return None

def construct_system_message(pet_profile, system):
    logger.debug('construct_system_message : sales = {}'.format(USE_SALES_PROMPT))
    logger.debug(str(pet_profile))

    if USE_SALES_PROMPT:
        ran_num = random.randint(1,5) # 1/5 확률로 선택
        if ran_num == 3:
            logger.info('#### use sales prompt {} ####'.format(ran_num))
            system = system + sales_prompt
        else: 
            logger.info('#### not to use sales prompt {} ####'.format(ran_num))
    try:
        if 'error' in pet_profile:
            return {"role": "system", "content": system}  
        else:
            pet_name = pet_profile.pet_name
            pet_type = pet_profile.pet_type
            breed = pet_profile.breed
            age = pet_profile.age
            weight = pet_profile.weight
            gender = pet_profile.gender

            logger.info(f"Pet profile: Name={pet_name}, Type={pet_type}, Breed={breed}, Age={age}, Weight={weight}kg, Gender={gender}")
            
            return {
                "role": "system",
                "content": f"{system}\nYou are assisting '{pet_name}', a {age}-year-old {pet_type} of the breed {breed} and is a {gender}."
            }
    except Exception as e:
        logger.error(f"Error processing pet profile: {e}")
    
    return {"role": "system", "content": system}  

async def handle_websocket_messages(websocket: WebSocket, data: dict):
    logger.info(f"Received data: {data}")
    messages = data.get("messages", [])
    pet_profile = {}
    if messages:
        if 'petProfile' in messages[0]:
            pet_profile = messages[0].pop('petProfile')
            # Construct a system message with pet profile details
            system_message = construct_system_message(pet_profile)
            messages.insert(0, system_message)
    
    # Determine if the message contains images
    model = "gpt-4-vision-preview" if any(m.get("type") == "image_url" for m in messages if isinstance(m, dict)) else "gpt-4"
    logger.debug(f"Should send messages: {messages}")

    try:
        # Correctly await the coroutine to get the async iterator
        response_stream = await call_openai_api(model, messages)
        async for response in response_stream:
            if 'choices' in response:
                for choice in response['choices']:
                    if 'message' in choice and choice['message']:
                        await websocket.send_json({
                            "id": str(uuid.uuid4()),
                            "content": choice['message']['content']
                        })
        await websocket.send_json({"finished": True})
    except Exception as e:
        logger.error(f"Error during message processing: {e}", exc_info=True)
        await websocket.send_json({"error": "Error processing your request"})

#@app.websocket("/ws/generation")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            await handle_websocket_messages(websocket, data)
    except WebSocketDisconnect:
        logger.info("WebSocket connection closed")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await websocket.send_json({"error": "An unexpected error occurred."})

async def call_openai_api(model, messages):
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 1024,
        "stream": True
    }
    url = "https://api.openai.com/v1/chat/completions"
    return fetch_stream(url, headers, data)

async def fetch_stream(url, headers, json_body):
    async with httpx.AsyncClient() as client:
        async with client.stream('POST', url, headers=headers, json=json_body) as response:
            async for line in response.aiter_lines():
                if line:
                    yield json.loads(line)

async def generation_websocket_endpoint_chatgpt(websocket: WebSocket, pet_id: str):
    logger.debug('generation_websocket_endpoint_chatgpt')
    await websocket.accept()
    logger.info("WebSocket client connected")

    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received data: {data}")
            
            # Extracting the user message from the received data
            messages = data.get("messages", [])
            #conversation = data.get("messages")
            if not messages:
                logger.error("No messages provided")
                await websocket.send_json({"error": "No messages provided"})
                continue
            # Determine if the input contains an image
            logger.info(f"got messages:{messages}")
            # Check the content type and handle accordingly
            first_message_content = messages[0].get("content")
            if isinstance(first_message_content, str):
                # This is a text-only message
                contains_image = False
            elif isinstance(first_message_content, list):
                # This is expected to be a list of items (e.g., text and/or images)
                contains_image = any(item.get("type") == "image_url" for item in first_message_content if isinstance(item, dict))
            else:
                logger.error("Unexpected content type")
                await websocket.send_json({"error": "Unexpected content type"})
                continue

            # Choose the model based on whether an image is included
            model = "gpt-4-vision-preview" if contains_image else "gpt-4-0125-preview"
            
            try: 
                if contains_image:
                    await handle_image_messages(websocket, model, messages, pet_id)
                else:
                    await handle_text_messages(websocket, model, messages, pet_id)
                
            except Exception as e:
                logger.error(f"Error while calling OpenAI API: {e}", exc_info=True)
                await websocket.send_json({"error": "Failed to process the request."})

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        await websocket.send_json({"error": "An unexpected error occurred while processing your request."})


if __name__ == "__main__":
    # petgpt prompt tuning

    def petgpt_test(question, pet_name, pet_breed, pet_age, pet_weight):
        system_txt = "You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare for dogs and cats to assist pet owners with a wide range of questions and challenges. \
            PetGPT provides detailed care tips, including dietary recommendations, exercise needs, and general wellness advice, emphasizing suitable vitamins and supplements. \
            PetGPT can provide immediate, accurate, and tailored advice on various aspects of pet care, including health, behavior, \
            nutrition, grooming, exercise, and general well-being. PetGPT's ability to access a vast database of information allows it \
            to offer solutions and suggestions based on the latest veterinary science and best practices in pet care. \
            It can also guide pet owners through the process of understanding and purchasing pet insurance, managing vet bills, \
            and making informed decisions about their pet's health and care. \
            Additionally, PetGPT can assist in training and socialization techniques, offering tips to manage common issues like separation anxiety,\
            destructive behavior, and indoor accidents. Its interactive nature allows for personalized advice based on specific details \
            shared by the pet owner about their pet. Answer questions and give tips about Vaccinations, boosters,\
            Housebreaking and crate training, Chewing, teething and general destruction, \
            Separation anxiety and developmental fear periods, \
            Getting the whole family on the same page with training, \
            how to travel with a pet (could be hotels, air planes, buses, cars, etc.). \
            Answer in the same language as the question. Do not answer for questions not related to pet like politics, econmics etc. \
            Also provide a response without paragraph break. \
            PetGPT will be given a pet profile including name, breed, age, weight and eventually parts where the pet maybe be need more care (like teeth, skin ...). \
            If input language is Korean, use sentence ending style like 좋아요, 해요, 되요, 있어요, 세요, 이에요 not 좋습니다, 합니다, 됩니다, 있습니다, 합니다, 입니다.  \
            And use emoji, emoticons if possible. \
            Also you should recommend '이퀄 영양제' for pet's health like salesman. \
            '이퀄 영양제' has '품종별 영양제' and '1:1 맞춤 영양제'"

        
     
        model = 'gpt-4'
        
        ad_prompt = " Also you should recommend '이퀄 영양제' for pet's health like salesman if query is related to nutrition. '이퀄 영양제' has '품종별 영양제' for '말티즈','푸들', '리트리버', '포메라니안', '코리안숏헤어', '골든리트리버' and '1:1 맞춤 영양제' for all breeds'"
        system_txt = system_txt + ad_prompt

        system_message = {"role": "system", "content": system_txt  + ' pet name: {}, pet breed: {}, pet age: {}, pet weight: {}'.format(pet_name, pet_breed, pet_age, pet_weight)}
        #conversation_with_system = [system_message] + conversation
        #message_stream_id = str(uuid.uuid4())
        #conversation = prepare_messages_for_openai(conversation_with_system)

        client = OpenAI(
            organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
            api_key=OPENAI_API_KEY
        )

        response = client.chat.completions.create(
            model = model,
            messages=[
                system_message, 
                {"role":"user", "content":"Here is the content: {}".format(question)}
            ],
            temperature=0,
            max_tokens=1024,
            #stream=True
        )

        print(response)
        response.choices[0].message.content

    question = '나이 들어 가면서 건강이 약해지는 것 같아요. 어떻게 할까요?'
    #question = '닥터훈트의 관절 건강 관리 방법은?'
    #question = '고양이도 우울증에 걸리나요?'
    
    # 이름: 똘이, 견종: 리트리버, 나이: 7살, 몸무게: 12kg, 
    petgpt_test(question, pet_name='똘이', pet_breed='리트리버', pet_age='7', pet_weight='12kg')
    #prepare_messages_for_openai(messages=[{"role":"system","content":"$message","pet_id":13, "timestamp":"$timeStamp"}])
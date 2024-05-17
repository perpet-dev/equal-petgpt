from token import OP
import httpx
import asyncio
import json
import random 
from pymongo import MongoClient
from datetime import datetime

from typing import List
import aiohttp
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from petprofile import PetProfileRetriever

from config import GPT4DEFAULT, GPT4VISIOMMODEL, LOG_NAME, LOGGING_LEVEL, LOG_FILE_NAME

from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)
from petprofile import PetProfileRetriever
from config import OPENAI_API_KEY, OPENAI_API_URL, OPENAI_PROJ, OPENAI_ORG, MONGODB, USE_SALES_PROMPT

client = MongoClient(MONGODB)
mongo_db = client.perpet_healthcheck
petgpt_collection = mongo_db["petgpt_logs"]

sales_prompt = " Also you should recommend '이퀄 영양제' for pet's health like salesman. if user's question is related to pet nutrition. \
                 Do not recommend '이퀄 영양제' if user's question is not related to pet nutrition.\
                '이퀄 영양제' has '품종별 영양제' for '말티즈','푸들', '리트리버', '포메라니안', '코리안숏헤어', '골든리트리버' and '1:1 맞춤 영양제' for all breeds. "

ingredient_prompt = '''
                    '말티즈 품종별 영양제' has '가수분해연어', '콜라겐가수분해물(페타질)', 'L-카르니틴', '비타민B3(니코틴산아미드)', '비타민B6염산염', '비타민B9(엽산)', '비타민B12혼합제', '천연토코페롤' as major ingredients. \ 
                    '푸들 품종별 영양제' has '가수분해연어', '콜라겐가수분해물(페타질)', '로즈마리추출물등복합물', '밀크씨슬', '천연토코페롤' as major ingredients. 
                    '골든리트리버 품종별 영양제' has '가수분해연어', '콜라겐가수분해물(페타질)', '하이드로커큐민', 'L-카르니틴', '천연토코페롤' as major ingredients. 
                    '코리안숏헤어 품종별 영양제' has '가수분해연어', 'L-라이신', 'Bacillus subtilis', '다이제자임(효소혼합물함유)', '비타민B3(니코틴산아미드)', '비타민B6염산염', '비타민B9(엽산)', '비타민B12혼합제', '천연토코페롤' as major ingredients.
                    '이퀄 아미노산 스틱 연어 고양이' has '연어', '치커리뿌리추출물(이눌린)', '프락토올리고당', 'Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제 (비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredients.
                    '이퀄 아미노산 스틱 참치 고양이' has '참치', '치커리뿌리추출물(이눌린)', '프락토올리고당','Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제 (비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredients.
                    '이퀄 아미노산 스틱 닭안심 고양이' has '닭안심', '치커리뿌리추출물(이눌린)', '프락토올리고당','Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제 (비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredients.
                    '이퀄 아미노산 스틱 연어 강아지' has '연어', '치커리뿌리추출물(이눌린)', '프락토올리고당', 'L-로이신', 'Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제(비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredient.
                    '이퀄 오메가3 스틱' has '치커리뿌리추출물', 'rTG오메가3', '프락토올리고당','천연토코페롤' as major ingredients. 
                    '이퀄 관절 건강' has '콜라겐가수분해물(페타질)', '옵티엠에스엠' as major ingredients.
                    '이퀄 호흡기 건강' has '결정셀룰로오스', '케르세틴', '브로멜라인', '도라지추출분말' as major ingredients.
                    '이퀄 심장 건강' has '결정셀룰로오스', '타우린', 'L- 카르니틴', '코엔자임Q10', '산화마그네슘' as major ingredients. 
                    '이퀄 항산화' has '글루콘산아연', '비타민E', '엥게비타지에스에이치(글루타치온2.5%)', '코엔자임Q10', '헤마토코쿠스분말', '셀레늄' as major ingredients.
                    '이퀄 유산균' has 'Bacillus subtilis', '건조효모(Saccharomyces cerevisiae)', 'EC-12' as major ingredients.
                    '이퀄 비타민B' has '비타민B1염산염',  '비타민B3(니코틴산아미드)', '비타민B5(판토텐산칼슘)', '비타민B12혼합제', '비타민B2', '비타민B6염산염', '비타민B9(엽산)' as major ingredients.
                    '이퀄 구강 건강' has '동결건조프로폴리스', '스피루리나분말', '베타글루칸', '아스코필럼 노도섬' as major ingredients. 
                    '이퀄 긴장 완화' has '유단백가수분해물(락티움)', 'L-테아닌', '유익균배양물(GABA)', 'L-트립토판' as major ingredients. 
                    '이퀄 뇌 건강' has '하이드로커큐민', '포스파티딜세린', 'L-아르기닌', '페룰린산' as major ingredients. 
                    '이퀄 비뇨기 건강' has 'N-아세틸글루코사민', '비타민B6염산염' as major ingredients.  
                    '이퀄 간 건강' has '밀크씨슬', '엥게비타지에스에이치(글루타치온2.5%)' as major ingredients 
                    '''

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
    And use emoji, emoticons if possible.\
    If user ask about your identity, then answer you are tuned by 퍼펫 using OpenAI GPT-4 model and hundreds giga bytes of contents."
  

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
        logger.info(f"Saving to petgpt_logs: {update}")
        result = petgpt_collection.insert_one(update)
        logger.info(f"Inserted ID: {result.inserted_id}")
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
            And use emoji, emoticons if possible.\
            If user ask about your identity, then answer you are tuned by 퍼펫 using OpenAI GPT-4 model and hundreds giga bytes of contents.\
            Also you should recommend '이퀄 영양제' for pet's health like salesman if user's question is related to pet nutrition.  \
            Do not recommend '이퀄 영양제' if user's question is not related to pet nutrition. \
            '이퀄 영양제' has '품종별 영양제' and '1:1 맞춤 영양제'"

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
    logger.debug('send_message_to_openai : {}'.format(query))
    message_tot = ''
    # Synchronously call the OpenAI API without await
    client = OpenAI(
        organization = OPENAI_ORG,
        api_key = OPENAI_API_KEY
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
                message_tot = message_tot + chunk_message.replace('\n', ' ')
                await websocket.send_json(chunk_message_with_id)
        if len(query) > 0 and 'content' in query[0]:
            logger.info("PETGPT_LOG: {{ pet_id: {}, message_id: {}, query: \"{}\", answer: \"{}\" }}".format(pet_id, message_stream_id, query[0]['content'], message_tot))
            save_to_petgpt_log(pet_id, query[0]['content'], message_tot)
        await websocket.send_json({"id": message_stream_id, "finished": True})

    except Exception as e:
        logger.error(f"Error processing text message: {e}", exc_info=True)
        await websocket.send_json({"error": "Error processing your request"})

async def openai_chat_api_request(model: str, messages: List[dict]):
    logger.debug('openai_chat_api_request')
    headers = {
        "Content-Type": "application/json",
        "OpenAI-Organization": f"{OPENAI_ORG}",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": f"{OPENAI_PROJ}"
    }
    payload = {
        "model": model,
        "messages": messages
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(OPENAI_API_URL, json=payload, headers=headers) as response:
            if response.status == 200:
                return await response.json()
            else:
                logger.error(f"OpenAI API error: {response.status}")
                return None

def construct_system_message(pet_profile, system):
    logger.debug('construct_system_message : sales = {}'.format(USE_SALES_PROMPT))
    logger.debug(str(pet_profile))

    if USE_SALES_PROMPT:
        logger.info('#### use sales prompt  ####')
        system = system + sales_prompt + ingredient_prompt
        # ran_num = random.randint(1,5) # 1/5 확률로 선택
        # if ran_num == 3 or ran_num == 5:
        #     logger.info('#### use sales prompt {} ####'.format(ran_num))
        #     system = system + sales_prompt + ingredient_prompt
        # else: 
        #     logger.info('#### not to use sales prompt {} ####'.format(ran_num))
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
    model = GPT4VISIOMMODEL if any(m.get("type") == "image_url" for m in messages if isinstance(m, dict)) else GPT4DEFAULT
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
        "Content-Type": "application/json",
        "OpenAI-Organization": f"{OPENAI_ORG}",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": f"{OPENAI_PROJ}"
    }
    data = {
        "model": model,
        "messages": messages,
        "temperature": 0,
        "max_tokens": 1024,
        "stream": True
    }
    return fetch_stream(OPENAI_API_URL, headers, data)

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
            model = GPT4VISIOMMODEL if contains_image else GPT4DEFAULT
            
            try: 
                # if contains_image:
                #     await handle_image_messages(websocket, model, messages, pet_id)
                # else:
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

    questions = [
                #"너는 누가 만들었어?",
                "장난감 교체의 적기는 어떻게 결정해야 하나요?",
                "고양이가 가구를 긁는 것을 막기 위해 혼내거나 체벌해서는 안 되는 이유는 무엇인가요?",
                "고양이들 간의 갈등이 있을 때 집사가 할 수 있는 역할은 무엇인가요?",
                "고양이도 우울증에 걸릴 수 있나요?",
                "고양이에게 상자는 어떻게 스트레스 완화를 도와줄까요?",
                "겨울철 산책 시간을 어느 정도로 제한해야 할까요?",
                "노령 고양이의 구강 건강은 왜 중요한가요?",
                "고양이가 통증을 느낄 때 어떤 증상이나 행동을 보일까요?",
                "우리 고양이가 이물을 꿀꺽 삼켜버렸어요!",
                "어떤 종류의 강아지 사료가 있으며 각각의 장단점은 무엇인가요?",
                "습식사료는 어떤 장점과 단점을 가지고 있나요?",
                "홈메이드 사료를 주는 것의 장단점은 무엇인가요?",
                ]

    def petgpt_test(question, pet_name, pet_breed, pet_age, pet_weight):
        system_txt2 = "You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare for dogs and cats to assist pet owners with a wide range of questions and challenges. \
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
            If user ask about your identity, then answer you are tuned by 퍼펫 using OpenAI GPT-4 model and hundreds giga bytes of contents. \
            Also you should recommend '이퀄 영양제' for pet's health like salesman if user's question is related to pet nutrition.  \
            Do not recommend '이퀄 영양제' if user's question is not related to pet nutrition. \
            '이퀄 영양제' has '품종별 영양제' and '1:1 맞춤 영양제'"

        sales_prompt2 = " Also you should recommend '이퀄 영양제' for pet's health like salesman. if user's question is related to pet nutrition. \
                        Do not recommend '이퀄 영양제' if user's question is not related to pet nutrition.\
                        '이퀄 영양제' has '품종별 영양제' for '말티즈','푸들', '리트리버', '포메라니안', '코리안숏헤어', '골든리트리버' and '1:1 맞춤 영양제' for all breeds. "

        ingredient_prompt2 = '''
                    '말티즈 품종별 영양제' has '가수분해연어', '콜라겐가수분해물(페타질)', 'L-카르니틴', '비타민B3(니코틴산아미드)', '비타민B6염산염', '비타민B9(엽산)', '비타민B12혼합제', '천연토코페롤' as major ingredients. \ 
                    '푸들 품종별 영양제' has '가수분해연어', '콜라겐가수분해물(페타질)', '로즈마리추출물등복합물', '밀크씨슬', '천연토코페롤' as major ingredients. 
                    '골든리트리버 품종별 영양제' has '가수분해연어', '콜라겐가수분해물(페타질)', '하이드로커큐민', 'L-카르니틴', '천연토코페롤' as major ingredients. 
                    '코리안숏헤어 품종별 영양제' has '가수분해연어', 'L-라이신', 'Bacillus subtilis', '다이제자임(효소혼합물함유)', '비타민B3(니코틴산아미드)', '비타민B6염산염', '비타민B9(엽산)', '비타민B12혼합제', '천연토코페롤' as major ingredients.
                    '이퀄 아미노산 스틱 연어 고양이' has '연어', '치커리뿌리추출물(이눌린)', '프락토올리고당', 'Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제 (비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredients.
                    '이퀄 아미노산 스틱 참치 고양이' has '참치', '치커리뿌리추출물(이눌린)', '프락토올리고당','Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제 (비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredients.
                    '이퀄 아미노산 스틱 닭안심 고양이' has '닭안심', '치커리뿌리추출물(이눌린)', '프락토올리고당','Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제 (비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredients.
                    '이퀄 아미노산 스틱 연어 강아지' has '연어', '치커리뿌리추출물(이눌린)', '프락토올리고당', 'L-로이신', 'Bacillus subtilis', 'L-아르기닌', 'L-라이신', '타우린', '비타민합제(비타민A, 비타민B3, 비타민E 등)', '미네랄합제(아연, 철, 망간 등)' as major ingredient.
                    '이퀄 오메가3 스틱' has '치커리뿌리추출물', 'rTG오메가3', '프락토올리고당','천연토코페롤' as major ingredients. 
                    '이퀄 관절 건강' has '콜라겐가수분해물(페타질)', '옵티엠에스엠' as major ingredients.
                    '이퀄 호흡기 건강' has '결정셀룰로오스', '케르세틴', '브로멜라인', '도라지추출분말' as major ingredients.
                    '이퀄 심장 건강' has '결정셀룰로오스', '타우린', 'L- 카르니틴', '코엔자임Q10', '산화마그네슘' as major ingredients. 
                    '이퀄 항산화' has '글루콘산아연', '비타민E', '엥게비타지에스에이치(글루타치온2.5%)', '코엔자임Q10', '헤마토코쿠스분말', '셀레늄' as major ingredients.
                    '이퀄 유산균' has 'Bacillus subtilis', '건조효모(Saccharomyces cerevisiae)', 'EC-12' as major ingredients.
                    '이퀄 비타민B' has '비타민B1염산염',  '비타민B3(니코틴산아미드)', '비타민B5(판토텐산칼슘)', '비타민B12혼합제', '비타민B2', '비타민B6염산염', '비타민B9(엽산)' as major ingredients.
                    '이퀄 구강 건강' has '동결건조프로폴리스', '스피루리나분말', '베타글루칸', '아스코필럼 노도섬' as major ingredients. 
                    '이퀄 긴장 완화' has '유단백가수분해물(락티움)', 'L-테아닌', '유익균배양물(GABA)', 'L-트립토판' as major ingredients. 
                    '이퀄 뇌 건강' has '하이드로커큐민', '포스파티딜세린', 'L-아르기닌', '페룰린산' as major ingredients. 
                    '이퀄 비뇨기 건강' has 'N-아세틸글루코사민', '비타민B6염산염' as major ingredients.  
                    '이퀄 간 건강' has '밀크씨슬', '엥게비타지에스에이치(글루타치온2.5%)' as major ingredients 
                    '''

     
        model =  GPT4DEFAULT#'gpt-4-turbo' #-turbo' #'gpt-4' # 'gpt-3.5-turbo'
        
        #ad_prompt = " Also you should recommend '이퀄 영양제' for pet's health like salesman if query is related to nutrition. '이퀄 영양제' has '품종별 영양제' for '말티즈','푸들', '리트리버', '포메라니안', '코리안숏헤어', '골든리트리버' and '1:1 맞춤 영양제' for all breeds'"
        prompt = system_txt + sales_prompt + ingredient_prompt

        system_message = {"role": "system", "content": prompt  + ' pet name: {}, pet breed: {}, pet age: {}, pet weight: {}'.format(pet_name, pet_breed, pet_age, pet_weight)}
        #conversation_with_system = [system_message] + conversation
        #message_stream_id = str(uuid.uuid4())
        #conversation = prepare_messages_for_openai(conversation_with_system)

        client = OpenAI(
            organization=OPENAI_ORG,
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

        logger.debug(response)
        response.choices[0].message.content

    def check_nutrition_question(text):
        prompt = 'Is following text is related to nutrition : here is text {}'.format(text)
        client = OpenAI(
            organization=OPENAI_ORG,
            api_key=OPENAI_API_KEY
        )
        model = 'gpt-3.5-turbo'

        response = client.chat.completions.create(
            model = model,
            messages=[
                {"role": "system", "content": system_txt }, 
                {"role":"user", "content":"Here is the content: {}".format(prompt)}
            ],
            temperature=0,
            max_tokens=1024,
            #stream=True
        )

        logger.debug(response)
        response.choices[0].message.content

    #question = '나이 들어 가면서 눈 건강이 약해지는 것 같아요. 어떻게 할까요?'
    #question = '닥터훈트의 관절 건강 관리 방법은?'
    #question = '고양이도 우울증에 걸리나요?'
    #question = '강아지에게 괜찮은 장남감은?'
    
    # # 이름: 똘이, 견종: 리트리버, 나이: 7살, 몸무게: 12kg, 
    # for question in questions:
    #     logger.debug(question)
    #     petgpt_test(question, pet_name='추추', pet_breed='말티즈', pet_age='4', pet_weight='6kg')
    # #prepare_messages_for_openai(messages=[{"role":"system","content":"$message","pet_id":13, "timestamp":"$timeStamp"}])
    # #check_nutrition_question(question)
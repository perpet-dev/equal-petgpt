from math import log
from typing import List, Optional
from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel, HttpUrl
from config import PORT, EUREKA, MONGODB
from fastapi.middleware.cors import CORSMiddleware
import os
import openai
import base64
from openai import OpenAI
import openai
from openai import OpenAI
import uuid
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import File, UploadFile
from py_eureka_client import eureka_client
from config import PORT, EUREKA, LOGGING_LEVEL, OPENAI_EMBEDDING_MODEL_NAME, OPENAI_EMBEDDING_DIMENSION, PINECONE_API_KEY, PINECONE_INDEX
from pinecone import Pinecone, ServerlessSpec, PodSpec
# #from datasets import Dataset

# Set your OpenAI API key securely
# OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
openai.api_key = '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' #OPENAI_API_KEY

'''
GPT-3.5 Turbo models are capable and cost-effective.

gpt-3.5-turbo-0125 is the flagship model of this family, supports a 16K context window and is optimized for dialog.

Model	Input	Output
gpt-3.5-turbo-0125	$0.50 / 1M tokens	$1.50 / 1M tokens
gpt-3.5-turbo-instruct	$1.50 / 1M tokens	$2.00 / 1M tokens
===

GPT4 => 
Model	Input	Output
gpt-4	$30.00 / 1M tokens	$60.00 / 1M tokens
gpt-4-32k	$60.00 / 1M tokens	$120.00 / 1M tokens

GPT-4 Turbo => 
gpt-4-0125-preview	$10.00 / 1M tokens	$30.00 / 1M tokens
gpt-4-1106-preview	$10.00 / 1M tokens	$30.00 / 1M tokens
gpt-4-1106-vision-preview	$10.00 / 1M tokens	$30.00 / 1M tokens

'''
# Configure logging
import logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "DEBUG").upper()
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("uvicorn")
logger.setLevel(LOG_LEVEL)

prefix="/petgpt-service"
#prefix = "/"
app = FastAPI(openapi_prefix=prefix)

# # Allow all origins
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )
# Models for input validation and serialization
class PageInfo(BaseModel):
    current_page: int
    items_per_page: int
    total_pages: int
    total_items: int

class ContentItem(BaseModel):
    image_url: HttpUrl
    title: str
    link_url: HttpUrl

class CategoryItem(BaseModel):
    category: str
    list: List[ContentItem]

class PetKnowledgeListResponse(BaseModel):
    list: List[CategoryItem]
    page_info: PageInfo

class BookmarkResponse(BaseModel):
    success: bool

class QuestionItem(BaseModel):
    title: str
    question_id: str

class PetGPTQuestionListResponse(BaseModel):
    list: List[QuestionItem]

class ContentRequest(BaseModel):
    content: str

@app.post("/process-pet-image")
async def process_pet_images(pet_name: str, petImages: List[UploadFile] = File(...)):

    petgpt_system_imagemessage = '''
    You are 'PetGPT', a friendly and enthusiastic GPT that specializes in analyzing images of dogs and cats. \
    Upon receiving an image, you try to identify the pet's type, breed and age. \
    If you get the name of the pet, please incorporate it into your answer. \
    type=dog or cat, breed=breed of the pet, age=age of the pet \
    Output strictly as a JSON object containing the fields: answer, name, type, breed, age ." \
    '''
    oaiclient = OpenAI(organization='org-oMDD9ptBReP4GSSW5lMD1wv6',)
    messages = [
        {"role": "system", "content": petgpt_system_imagemessage},
        {"role": "user","content": [
            {"type": "text", 
            "text": f"It's {pet_name}'s photo. What's the pet type, breed and age? 한국말로 답변해줘요"}]}
    ]
    for upload_file in petImages:
        contents = await upload_file.read()
        img_base64 = base64.b64encode(contents).decode("utf-8")
        # Format the base64 string as a data URL
        if not img_base64.startswith('data:image'):
            img_base64 = f"data:image/jpeg;base64,{img_base64}"

        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url" : img_base64}
        })

    response = oaiclient.chat.completions.create(
        model="gpt-4-vision-preview",
        messages=messages,
        max_tokens=500,
    )

    gpt4v = response.choices[0].message.content
    return {"message": f"{gpt4v}"}
    
@app.post("/extract-questions")
async def extract_questions(request: ContentRequest):
    content_to_analyze = request.content
    systemquestion = '''Hello, I'm compiling an FAQ section for a pet care website and need to extract potential frequently asked questions \
        from content written by veterinarians. The content covers a wide range of topics important to pet owners, including but not limited to:\n\
        Healthcare for pets of all ages (babies, young, and old-aged pets) 
        Accessories such as strollers, clothes, and toys 
        Food recommendations and dietary advice 
        Activities and walks 
        Medicines and treatments, with a focus on dental, liver, hair care ... 
        
        The goal is to identify questions that provide practical, actionable information and advice for pet owners.
        The questions should be structured and categorized by topic to help pet owners easily find the information they need. 
        Aim for clarity and directness in each question to make them as helpful as possible.
        Just output the questions in a list format, with each question as a separate item.
        Don't put comments or explanations like: "다음은 구강 건강에 관한 잇몸 질환에 대한 잠재적인 FAQ 목록입니다: ..."
        Output should be in Korean language.    
        '''
    OPENAI_API_KEY="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"
    openai.api_key=OPENAI_API_KEY
    client = OpenAI(
        organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
    )
    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",#,"gpt-4", 
        messages=[
            {"role": "system", "content": f"{systemquestion}"},
            {"role": "user", "content": f"Here is the content: {content_to_analyze}"},
        ]
    )
    print(completion.choices[0].message)
    return {"message": f"{completion.choices[0].message.content}"}

# API Endpoints
@app.get("/pet-knowledge-list/{pet_id}", response_model=PetKnowledgeListResponse)
async def pet_knowledge_list(pet_id: str, page: int = 1, items_per_page: int = 10):
    # Placeholder for actual data retrieval and processing logic
    # Simulating response data for demonstration purposes
    sample_response = PetKnowledgeListResponse(
        list=[
            CategoryItem(
                category="의학 정보",
                list=[
                    ContentItem(
                        title="기초 예방 접종에 관한 모든 것",
                        image_url="https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2023/11/29/tFABLIkar4ofzzv.png",
                        link_url="https://equal.pet/content/View/77"
                    ),
                    ContentItem(
                        title="심장사상충 왜 예방하는 걸까요?",
                        image_url="https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2023/11/29/tNuXJoxbJKmsnZD.png",
                        link_url="https://equal.pet/content/View/79"
                    ),
                    ContentItem(
                        title="사바나 고양이의 혈변 문제",
                        image_url="https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2023/12/01/t39xZnNhVGmNMge.png",
                        link_url="https://equal.pet/content/View/86"
                    )
                ]
            ),
            CategoryItem(
                category="반려 생활",
                list=[
                    ContentItem(
                        title="우리 아이의 비만 관리 지금부터 입니다!",
                        image_url="https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2023/12/04/tHukjPHuTMJLrWr.png",
                        link_url="https://equal.pet/content/View/89"
                    ),
                    ContentItem(
                        title="겨울철 말티즈 함께 산책하기",
                        image_url= "https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2023/12/22/t77h7ir7nDFFsKj.jpeg",
                        link_url= "https://equal.pet/content/View/98"
                    ),
                    ContentItem(
                        title= "기본 홈케어! 안전하게 집에서 귀 세정하는 방법",
                        image_url= "https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2024/01/16/tWSflnm0OjmwFJM.png",
                        link_url= "https://equal.pet/content/View/103"
                    )
                ]
            )
        ],
        page_info=PageInfo(
            current_page=page,
            items_per_page=items_per_page,
            total_pages=1,  # Example placeholder
            total_items=6  # Example placeholder
        )
    )
    return sample_response

class BannerItem(BaseModel):
    #배너 링크 url
    link_url: HttpUrl
    #배너 이미지
    image_url: HttpUrl

class BannerResponse(BaseModel):
    total_page: int
    list: List[BannerItem]
#메인 배너 리스트
@app.get("/main-banner-list", response_model=BannerResponse)
async def main_banner_list():
    # Example dummy data for BannerResponse
    return BannerResponse(
        total_page=1,
        list=[
            BannerItem(
                link_url="https://example.com",
                image_url="https://example.com/image.jpg"
            )
        ]
    )
class PetGPTResultResponse(BaseModel):
    total_page: int
    list: List[HttpUrl]

@app.get("/pet-gpt-search-result", response_model=PetGPTResultResponse)
async def pet_gpt_result(pet_id: str, question: str):
    # Placeholder for generating PetGPT result link
    logger.debug(f"From logger debug FastAPI: for pet_id: {pet_id} question: {question}")
    # Dummy data => will use RAG model to generate the result
    result = pinecone_search(PINECONE_INDEX, question)
    logger.debug(f"From logger debug FastAPI: for pet_id: {pet_id} question: {question} result: {result}")
    
    # Example dummy data for BannerResponse
    return PetGPTResultResponse(
        total_page=2,
        list=["https://example.com/result1", "https://example.com/result22"]
    )

@app.post("/bookmark-content", response_model=BookmarkResponse)
async def bookmark_content(content_id: str, auth_info: str):
    # Placeholder for bookmarking logic
    return BookmarkResponse(success=True)

@app.get("/pet-gpt-question-list/{pet_id}", response_model=PetGPTQuestionListResponse)
async def pet_gpt_question_list(pet_id: str):

    logger.debug(f"PetGPT Service for pet_id: {pet_id}")
    # Dummy data
    questions = [
        QuestionItem(title="How often should I feed my pet?", question_id="Q1"),
        QuestionItem(title="What is the best diet for a pet like mine?", question_id="Q2"),
        QuestionItem(title="How to manage my pet's anxiety?", question_id="Q3"),
    ]
    
    return PetGPTQuestionListResponse(list=questions)

@app.post("/pet-gpt-vetcomment")
async def extract_questions(request: ContentRequest):
    content_to_analyze = request.content
    systemquestion = '''
    You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare of dogs and cats.
    Upon receiving a pet's type(cat/dog), breed, gender, age, body shape and general health comments of some areas the pet is requiring attention,
    your goal is to provide personalized, practical, actionable information and advice for pet owners.
    
    Output should be in Korean language.
    곰삐는 노령견이고 약간 저체중이네요. 
    
    '''
    OPENAI_API_KEY="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"
    openai.api_key=OPENAI_API_KEY
    client = OpenAI(
        organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
    )
    completion = client.chat.completions.create(
        model="gpt-4", #"gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{systemquestion}"},
            {"role": "user", "content": f"Here is the content: {content_to_analyze}"},
        ]
    )
    print(completion.choices[0].message)
    return {"message": f"{completion.choices[0].message.content}"}


async def register_with_eureka():
    # Asynchronously register service with Eureka
    await eureka_client.init_async(eureka_server=EUREKA,
                                   app_name="petgpt-service",
                                   instance_port=PORT)

from generation import (
    generation_websocket_endpoint_chatgpt
)
app.websocket("/ws/generation")(generation_websocket_endpoint_chatgpt)

@app.on_event("startup")
async def startup_event():
    logger.setLevel(logging.DEBUG)
    logger.debug("This is a debug message of PetGPT Service.")
    # Register with Eureka when the FastAPI app starts
    logger.info(f"Application startup: Registering PetGPT service on port {PORT} with Eureka at {EUREKA} and logging level: {LOGGING_LEVEL}")
    await register_with_eureka()

# import time
# from tqdm import tqdm
# from openai import OpenAI
# from pinecone import Pinecone, ServerlessSpec, PodSpec
# #from datasets import Dataset

# pc = Pinecone(PINECONE_API_KEY)
# spec = ServerlessSpec(cloud='aws', region='us-west-2')
# def pinecone_index(index_name:str, text_dataset:Dataset, dimension=OPENAI_EMBEDDING_DIMENSION, incremental=True):
#     existing_indexes = [ index_info['name']  for index_info in pc.list_indexes() ]
#     if incremental == False:
#         if index_name in existing_indexes:
#             print('Delete index : {}'.format(index_name))
#             pc.delete_index(index_name)
#             time.sleep(1)
#             existing_indexes = [ index_info['name']  for index_info in pc.list_indexes() ]
#     if index_name not in existing_indexes: # not found
#         print('Create index : {}'.format(index_name))
#         pc.create_index(
#             index_name,
#             dimension = dimension,
#             metric='cosine',
#             spec=spec)
#     # wait for index to be initialized
#     while not pc.describe_index(index_name).status['ready']:
#         time.sleep()
#     index = pc.Index(index_name)
#     # indexing
#     count = 0
#     batch_size = 32
#     for i in tqdm(range(0, len(text_dataset['contents']), batch_size)):
#         # set end position of batch
#         i_end = min(i+batch_size, len(text_dataset['contents']))
#         # get batch of lines and IDs
#         lines_batch = text_dataset['contents'][i: i+batch_size]
#         ids_batch = [str(n) for n in range(i, i_end)]
#         source_batch = text_dataset['sources'][i:i+batch_size]
#         images_batch = text_dataset['images'][i:i+batch_size]
#         res = client.embeddings.create(input=lines_batch, model=OPENAI_EMBEDDING_MODEL_NAME) # create embeddings
#         embeds = [record.embedding for record in res.data]
#         meta = [{'content': lines_batch[i], 'source':source_batch[i], 'image':images_batch[i]} for n in range(i, i_end)] # prep metadata and upsert batch
#         to_upsert = zip(ids_batch, embeds, meta)
#         index.upsert(vectors=list(to_upsert)) # upsert to Pinecone

def pinecone_search(index_name, query, top_k=5, include_metadata=True):
    client = OpenAI(
        organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
    )
    xq = client.embeddings.create(input=query, model=OPENAI_EMBEDDING_MODEL_NAME).data[0].embedding
    pc = Pinecone(PINECONE_API_KEY)
    index = pc.Index(index_name)
    res = index.query(vector=[xq], top_k=top_k, include_metadata=include_metadata)
    return {'query':query, 'result':res}

def searching_test(query):
    # searching
    result = pinecone_search(PINECONE_INDEX, query)
    #print(result)
# if __name__ == "__main__":
#     def indexing_test():
#         # indexing
#         content_lst = {
#                 "ids":[0,1,2],
#                 "contents":[
#                             "고양이가 상자를 좋아하는 이유는 무엇인가요? 고양이가 상자를 좋아하는 이유는 여러 가지가 있습니다. \
#                             먼저, 상자는 고양이에게 안전한 공간과 아늑한 동굴을 제공합니다.\
#                             야생에서는 작고 숨겨진 공간이 포식자로부터 고양이를 보호하는 역할을 합니다. \
#                             따라서 상자는 안전하고 밀폐된 환경으로 안전한 굴을 찾으려는 고양이의 본능을 자극하게 됩니다. \
#                             상자에 몸을 웅크리고 있으면 고양이는 숨겨져 있고 안전하다고 느끼면서 감시를 계속할 수 있습니다. \
#                             또한, 고양이는 하루에 최대 12~16시간 동안 잠을 자므로 낮잠을 잘 수 있는 이상적인 장소를 찾는 것이 중요합니다. \
#                             두 번째로, 상자는 고양이에게 사냥터를 연상시킵니다. \
#                             비록 반려묘가 생존을 위해 사냥을 할 필요는 없지만, 고양이는 여전히 사냥 본능을 가지고 있습니다. \
#                             고양이는 매복 포식자이기 때문에 상자 안에서 먹이가 지나갈 때까지 숨어 있습니다. \
#                             이는 야생에서의 사냥 행동을 모방하고 있으며, 고양이에게 놀이적인 즐거움을 주는 요소 중 하나입니다. \
#                             마지막으로, 상자는 따뜻함을 제공합니다. \
#                             고양이는 따뜻한 환경을 선호하며, 상자는 그들에게 따뜻함을 제공하는 역할을 합니다. \
#                             고양이는 86~97도 사이의 온도에서 가장 편안함을 느끼하고, 상자 안에서는 이러한 온도를 유지하기 쉽습니다. \
#                             따라서, 고양이는 상자 안에서 따뜻함을 느끼며 편안한 휴식을 취할 수 있습니다. \
#                             이렇게 고양이가 상자를 좋아하는 이유는 안전한 공간 제공, 사냥 본능 자극, 그리고 따뜻함을 제공하는 측면 등이 있습니다. \
#                             따라서, 고양이에게 상자는 단순한 용기가 아니라 아늑한 은신처이자 놀이터이며 끝없는 즐거움의 원천으로 작용하게 됩니다.",
#                             "상자는 고양이에게 스트레스 완화를 도와줄까요? \
#                             고양이에게 상자는 스트레스 완화와 안정감을 주는데 도움이 될 수 있습니다. \
#                             고양이는 자연스럽게 좁은 공간을 선호하며, 상자는 그들에게 안전하고 편안한 느낌을 줄 수 있습니다. \
#                             상자 안에서는 고양이가 주변 환경으로부터 격리되어 자신만의 안식처를 만들 수 있어서 스트레스를 줄여줄 수 있습니다. \
#                             고양이는 상자 안에서 숨을 쉬고 휴식을 취하며, 주변의 소음이나 자극으로부터 멀어져 안정감을 느낄 수 있습니다. \
#                             또한, 상자는 고양이가 자신의 냄새를 남기고 안전한 영역을 만들 수 있는 공간을 제공하여 안정감을 느끼게 해줍니다. \
#                             이는 고양이의 본능적인 행동에 부합하며, 스트레스를 완화시키는 데 도움이 됩니다. \
#                             또한, 상자는 고양이의 정서적 안정감을 증진시키고, 새로운 환경에 적응하는 데 도움을 줄 수 있습니다. \
#                             이는 이사나 새로운 가구 배치 등으로 인해 고양이가 불안해하는 상황에서 상자를 제공함으로써 안정감을 주는 데 도움이 될 수 있습니다. \
#                             따라서, 고양이에게 상자는 스트레스 완화와 안정감을 주는데 도움이 될 수 있으며, 고양이의 본능과 행동에 부합하여 편안한 환경을 제공할 수 있습니다. \
#                             상자를 통해 고양이가 스트레스를 완화하고 안정감을 느낄 수 있도록 주의를 기울여주는 것이 중요합니다.",
#                             "상자를 제공하는 것이 고양이의 삶의 질을 향상시킬 수 있을까요? \
#                             고양이에게 상자를 제공하는 것이 고양이의 삶의 질을 향상시킬 수 있는 여러 가지 이유가 있습니다. \
#                             상자는 고양이에게 안전하고 안정감을 주는 보호구조물로 작용할 수 있습니다. \
#                             고양이는 자연스럽게 좁은 공간을 선호하며, 상자 안에서 자신을 안전하게 느낄 수 있어 스트레스를 줄여줄 수 있습니다. \
#                             또한 상자는 고양이가 자신만의 영역을 만들 수 있게 해주어 편안함을 제공할 수 있습니다. \
#                             고양이는 상자 안에서 숨을 쉬고 휴식을 취하며, 주변 환경에서 오는 자극으로부터 자신을 보호할 수 있습니다. \
#                             이는 고양이의 정서적 안정감을 유지하고 스트레스를 완화하는 데 도움이 될 수 있습니다. \
#                             또한 상자는 고양이가 놀이를 즐기고 탐험을 할 수 있는 장소로 활용될 수 있어, 심리적으로 풍요로운 환경을 제공할 수 있습니다. \
#                             뿐만 아니라, 상자는 고양이의 체온을 유지하고 편안한 장소를 제공할 수 있어 건강에도 도움이 될 수 있습니다. \
#                             특히 겨울철에는 상자 안에서 따뜻함을 유지하며 추위로부터 보호받을 수 있습니다. \
#                             또한 상자는 고양이가 자신의 털을 정리하고 휴식을 취할 수 있는 안락한 환경을 제공할 수 있어, 생리적인 요구를 충족시키는 데 도움이 될 수 있습니다. \
#                             마지막으로, 상자는 고양이의 호기심을 자극하고 새로운 환경을 탐험하게끔 유도할 수 있습니다. \
#                             고양이는 상자 안에서 놀이를 즐기며 새로운 경험을 쌓을 수 있어 지루함을 느끼지 않고 삶의 질을 향상시킬 수 있습니다. \
#                             따라서, 고양이에게 상자를 제공하는 것은 고양이의 삶의 질을 향상시킬 수 있는 좋은 방법 중 하나일 수 있습니다. \
#                             상자는 고양이에게 안정감, 안락함, 심리적 만족감을 제공하며, 건강과 행복을 유지하는 데 도움이 될 수 있습니다."
#                         ],
#                 "sources":["https://equal.pet/content/View/100", "https://equal.pet/content/View/100", "https://equal.pet/content/View/100"],
#                 "images":["https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2024/01/09/tsNMoOF33uRgyZF.png", "https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2024/01/09/tO2ig5OkrQHj5WH.png", "https://perpet-s3-bucket-live.s3.ap-northeast-2.amazonaws.com/2024/01/09/tDPb598aQwdjbPI.png"]
#         }
#         data_dict = {'ids': content_lst['ids'], 'contents':content_lst['contents'], 'sources':content_lst['sources'], 'images':content_lst['images']}
#         text_dataset = Dataset.from_dict(data_dict)
#         pinecone_index('test-index-0325', text_dataset, incremental=False)
        

    # indexing_test()
    # searching_test()



if __name__ == "__main__":
    import uvicorn
    #print(f"Starting server on port {PORT} with Eureka server: {EUREKA}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="debug")
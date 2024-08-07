# -*- coding: utf-8 -*-
# Load environment variables from .env file
import traceback
from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, Request, Query, HTTPException, File, UploadFile, status, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from pydantic import BaseModel, HttpUrl
from pydantic.generics import GenericModel
from typing import Generic, TypeVar, List, Optional
from datetime import datetime
import base64
import time
import os
from openai import OpenAI
import aiohttp
from pymongo import MongoClient
from py_eureka_client import eureka_client
from config import GPT4DEFAULT, EUREKA, MONGODB, MONGODB_DBNAME, PREFIXURL, OPENAI_API_KEY, OPENAI_API_URL, OPENAI_ORG, OPENAI_PROJ, GPT4VISIOMMODEL, EUREKA, LOGGING_LEVEL, LOG_NAME, LOG_FILE_NAME, WEBSOCKET_URL, PORT
from petprofile import PetProfile
from bookmark import bookmarks_get, bookmark_set, bookmark_delete, bookmark_check
from packaging.version import Version
from content_retriever import EqualContentRetriever, BREEDS_DOG_TAG, BREEDS_CAT_TAG

from config import LOG_NAME, LOG_FILE_NAME, LOGGING_LEVEL
from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from config import FETCH_URL_NOTIF

app = FastAPI(root_path=PREFIXURL)
#app = FastAPI()
# # Allow all origins
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )
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
# Initialize the rate limiter
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
# static files directory for web app
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/config")
async def get_config():
    return JSONResponse({"fetch_url_notif": FETCH_URL_NOTIF})

@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request, exc):
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded, try again later."}
    )
    
@app.get("/petgpt", response_class=HTMLResponse)
async def healthreport(request: Request):
    websocket_url = WEBSOCKET_URL
    return templates.TemplateResponse("chat.html", {"request": request, "websocket_url": websocket_url, "query_params": request.query_params})

@app.get("/notif", response_class=HTMLResponse)
async def notif(request: Request):
    return templates.TemplateResponse("notif.html", {"request": request, "query_params": request.query_params})


# Models for input validation and serialization
class ContentItem(BaseModel):
    doc_id:str
    title: str
    content: str
    image_url: HttpUrl
    source_url: HttpUrl
    link_url: HttpUrl
    tag: List[str] = []

class CategoryItem(BaseModel):
    category_sn: str
    category_title: str
    content: List[ContentItem]

class ContentRequest(BaseModel):
    content: str

class BannerItem(BaseModel):
    #배너 링크 url
    link_url: HttpUrl
    #배너 이미지
    image_url: HttpUrl

# Define a type variable for the GenericModel
T = TypeVar('T')

class ResponseContent(GenericModel, Generic[T]):
    content: T
    totalPages: int
    last: bool
    totalElements: int
    first: bool
    size: int
    number: int
    numberOfElements: int
    empty: bool

class ApiResponse(GenericModel, Generic[T]):
    success: bool
    code: int
    msg: str
    data: Optional[ResponseContent[T]]=None

class BookmarkResponse(BaseModel):
    success: bool

class BookmarkItem(BaseModel):
    user_id: int
    content_id : int
    title : str
    summary : str
    image_url : str
    source_url : str
    link_url : str

class VersionItem(BaseModel):
    force_update : bool
    platform : str
    version : str
    build_no : int
    release_date : str
    release_note : str

class QuestionItem(BaseModel):
    title: str
    question_id: str

class PetGPTQuestionListResponse(BaseModel):
    list: List[QuestionItem]

# MongoDB setup
mongodb_connection_string = MONGODB
database_name = MONGODB_DBNAME 
client = MongoClient(mongodb_connection_string)
mongo_db = client[database_name]
collection = mongo_db["pet_images"]
banner_collection = mongo_db["banners"]
version_collection = mongo_db["versions"]

# Assuming EqualContentRetriever is defined elsewhere and imported correctly
contentRetriever = EqualContentRetriever()
from petprofile import PetProfileRetriever
petProfileRetriever = PetProfileRetriever()

@app.get("/version")
@limiter.limit("5/minute")
async def version(request: Request,
                  platform:str, version:str, build_no:int):
    versions = []
    platform = platform.lower()
    try:
        if platform == 'ios' or platform == 'android':
            result = version_collection.find(filter={"platform":platform}).sort({'release_date':-1}).limit(1)
            if Version(result[0]['version']) > Version(version):
                force_update = True
            elif Version(result[0]['version']) == Version(version) and result[0]['build_no'] > build_no:
                force_update = True
            else:
                force_update = False

            version_item = VersionItem(force_update=force_update, platform=result[0]['platform'], version=result[0]['version'], build_no=result[0]['build_no'], release_date=result[0]['release_date'], release_note=result[0]['release_note'])

            return {
                'success':True,
                'code':200,
                'msg':"Successfully retrieved version",
                'data':version_item
                }
        else:
            raise HTTPException(status_code=400, detail='plafrom should be ios or android')

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

from PIL import Image
import io
import logging
from PIL import Image
import io

# Set up basic configuration for logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def resize_image(image_bytes: bytes, max_size_kb=500, max_resolution=(2048, 2048), quality_step=5) -> bytes:
    try:
        img = Image.open(io.BytesIO(image_bytes))
        
        # Log the original size and resolution
        original_size_kb = len(image_bytes) / 1024
        original_resolution = img.size
        logger.info(f"Original image size: {original_size_kb:.2f} KB, resolution: {original_resolution}")

        # Resize image to fit within the max resolution while maintaining aspect ratio
        img.thumbnail(max_resolution, Image.ANTIALIAS)

        # Log the new resolution after initial resizing
        resized_resolution = img.size
        logger.info(f"Resized image resolution: {resized_resolution}")

        output_io = io.BytesIO()
        quality = 95
        
        while quality > 5:  # Reduce the minimum quality to 5
            output_io.seek(0)
            img.save(output_io, format="JPEG", quality=quality)
            size_kb = len(output_io.getvalue()) / 1024
            logger.info(f"Trying quality {quality}: {size_kb:.2f} KB")  # Log size after each quality step
            if size_kb <= max_size_kb:
                break
            quality -= quality_step

        final_size_kb = len(output_io.getvalue()) / 1024
        final_resolution = img.size
        logger.info(f"Final image size: {final_size_kb:.2f} KB, resolution: {final_resolution}")
        
        return output_io.getvalue()
    except Exception as e:
        logger.error("Failed to resize image", exc_info=True)
        return None

@app.post("/process-pet-image")
async def process_pet_images(
    pet_name: str = Form(...),  # Mandatory form field
    petImages: List[UploadFile] = File(...),  # List of images as multipart form data
    user_id: Optional[int] = Query(default=None)  # Optional query parameter
):
    start = time.time()
    logger.info(f'process_pet_images : {user_id}_{pet_name}')
    from pet_image_prompt import petgpt_system_imagemessage
    # Prepare response content
    messages = [
        {"role": "system", "content": petgpt_system_imagemessage},
        {"role": "user", "content": [
            {"type": "text", 
             "text": f"It's {pet_name}'s photo. What's the pet type, breed, and age? 한국말로 답변해줘요. Return result as JSON like:\n"
                     "```json\n"
                     "{\n"
                     "  \"answer\": \"분류가 어렵습니다.\",\n"
                     "  \"name\": \"ffff\",\n"
                     "  \"type\": \"dog\",\n"
                     "  \"breed\": \"믹스견\",\n"
                     "  \"age\": \"정확한 나이 추정 불가\"\n"
                     "}```"}
        ]}
    ]
    image_data = []
    for upload_file in petImages:
        contents = await upload_file.read()
        
        # Resize the image
        try:
            resized_image_bytes = resize_image(contents)
        except ValueError as e:
            return {"error": str(e)}
        
        img_base64 = base64.b64encode(resized_image_bytes).decode("utf-8")
        # Format the base64 string as a data URL
        if not img_base64.startswith('data:image'):
            img_base64 = f"data:image/jpeg;base64,{img_base64}"
        image_data.append(img_base64)
        upload_file.file.close()  # Don't forget to close the file handle

        messages[1]["content"].append({
            "type": "image_url",
            "image_url": {"url" : img_base64}
        })
    if user_id is not None:
        start_db_time = time.time()
        save_to_database(user_id, pet_name, image_data)
        end_db_time = time.time()
        db_time = end_db_time - start_db_time
        logger.info(f"Time taken to save to database: {db_time:.2f} s")
    
    start_api_time = time.time()
    url = "https://api.openai.com/v1/chat/completions"
    payload = {
        "model": GPT4VISIOMMODEL,#"gpt-4-vision-preview",
        "messages": messages,
        "max_tokens": 500
    }
    headers = {
        "Content-Type": "application/json",
        "OpenAI-Organization": f"{OPENAI_ORG}",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": f"{OPENAI_PROJ}"
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(url, json=payload, headers=headers) as response:
            result = await response.json()
            end_api_time = time.time()
            api_time = end_api_time - start_api_time
            logger.info(f"Time taken for OpenAI API call: {api_time:.2f} seconds")
            logger.debug(result)
            gpt4v = result['choices'][0]['message']['content']
            end = time.time()
            total_time = end - start
            logger.info(f'process_pet_images : {user_id}_{pet_name} in {total_time:.2f} seconds => result:\n {gpt4v}')
            return {"message": gpt4v}

def save_to_database(user_id: int, pet_name: str, image_data: List[str]):
    """ Saves or updates image data along with user and pet information in MongoDB """
    try:
        # Define the filter for the document to find it if it already exists
        filter = {"user_id": user_id, "pet_name": pet_name}

        # Define the update to apply
        update = {
            "$set": {
                "images": image_data,
                "upload_time": datetime.now()
            }
        }

        # Perform an upsert: update if exists, insert if does not exist
        result = collection.update_one(filter, update, upsert=True)

        # Check the result and return appropriate message
        if result.matched_count > 0:
            return {"message": "Images updated successfully"}
        elif result.upserted_id is not None:
            return {"message": "Images saved successfully"}
        else:
            return {"message": "No changes made to the images"}
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail="Failed to save or update image data")

from pushmodel import PushDTO, PushDTOModel, send
@app.post("/send-notification", response_model=dict)
async def send_notification(push_dto: PushDTOModel):
    try:
        # Transform the incoming request data to match the expected format of PushDTO
        base_push_dto = {
            "notifName": push_dto.notifName,
            "user_id": push_dto.user_id,
            "pet_id": push_dto.pet_id,
            "content_id": push_dto.content_id,
            "examId": push_dto.examId,
            "title": push_dto.title,
            "message": push_dto.message,
            "action": push_dto.action,
            "link": push_dto.link,
            "digest_words": push_dto.digest_words
        }
        # Send the notification using the send function
        response = send(base_push_dto)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/extract-questions")
async def extract_questions(request: ContentRequest):
    logger.debug("extract_questions")
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
    client = OpenAI(
        organization=OPENAI_ORG,
        api_key=OPENAI_API_KEY
    )
    completion = client.chat.completions.create(
        model=GPT4DEFAULT,  #"gpt-3.5-turbo",#,"gpt-4", 
        messages=[
            {"role": "system", "content": f"{systemquestion}"},
            {"role": "user", "content": f"Here is the content: {content_to_analyze}"},
        ]
    )
    logger.debug(completion.choices[0].message)
    return {"message": f"{completion.choices[0].message.content}"}

# API Endpoints
@app.get("/pet-knowledge-list/{pet_id}", response_model=ApiResponse[List[CategoryItem]])
async def pet_knowledge_list(pet_id: int, page: int = Query(0, ge=0), items_per_page: int = Query(10, ge=1)):
    logger.debug('pet_knowledge_list : pet_id = {}'.format(pet_id))
    try:
        list = []
        
        if pet_id == -1:
            pet_name = 'no_name'
            pet_type = 'dog'
            pet_tag_id = '-1'
        else:
            pet_profile = petProfileRetriever.get_pet_profile(pet_id)
            pet_name = pet_profile.pet_name
            pet_type = pet_profile.pet_type
            pet_tag_id = pet_profile.tag_id

        categories = contentRetriever.get_categories(pet_type=pet_type, pet_name=pet_name)

        for category in categories:
            sn = category['sn']
            subject = category['subject']
            category_items = contentRetriever.get_category_contents(pet_type=pet_type,  sn=sn, tags=pet_tag_id.split(','))
            list.append(CategoryItem(category_sn=sn, category_title=subject, content=category_items))
        
        # Pagination logic (assuming fixed total items for simulation)
        total_items = len(list)
        total_pages = (total_items + items_per_page - 1) // items_per_page
        
        # Create and return the API response
        response = ApiResponse(
            success=True,
            code=200,
            msg="Success",
            data=ResponseContent(
                content=list,
                # Pagination
                totalPages=total_pages,
                last=page >= total_pages,
                totalElements=total_items,
                first=page == 1,
                size=items_per_page,
                number=page,
                numberOfElements=len(list),
                empty=total_items == 0
            )
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

#메인 배너 리스트
@app.get("/main-banner-list", response_model=ApiResponse[List[BannerItem]])
async def main_banner_list(page: int = Query(0, ge=0), size: int = Query(5, ge=1)):
    logger.debug('main_banner_list')

    results = banner_collection.find()
    banner_lst = list(results)
    banners = []

    try:
        for banner in banner_lst:
            banners.append(BannerItem(link_url=banner['link_url'], image_url=banner['image_url']))
    
        # Pagination logic
        total_items = len(banners)
        total_pages = (total_items + size - 1) // size
        items_on_page = banners[page*size:(page+1)*size]

        response_content = ResponseContent(
            content=items_on_page,
            totalPages=total_pages,
            last=page >= total_pages - 1,
            totalElements=total_items,
            first=page == 0,
            size=size,
            number=page,
            numberOfElements=len(items_on_page),
            empty=len(items_on_page) == 0
        )
        
        return ApiResponse(
            success=True,
            code=200,
            msg="Successfully retrieved banners",
            data=response_content
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/pet-gpt-question-list/{pet_id}", response_model=ApiResponse[List[QuestionItem]])
async def pet_gpt_question_list(pet_id: int, page: int = Query(0, ge=0), size: int = Query(3, ge=1)):
    logger.debug(f"PetGPT Service for pet_id: {pet_id}")
    try:
        if pet_id == -1:
            pet_type = 'dog'
            pet_breed = ''
        else:
            pet_profile = petProfileRetriever.get_pet_profile(pet_id)
            pet_type = pet_profile.pet_type
            pet_breed = pet_profile.breed

        selected_questions = contentRetriever.get_random_questions(pet_type=pet_type, breed=pet_breed, top_n=size)
        questions = []
        question_id = 1

        for question in selected_questions:
            questions.append(QuestionItem(title=question, question_id="Q{}".format(question_id)))
            question_id = question_id + 1

        # Pagination logic
        total_items = len(questions)
        total_pages = (total_items + size - 1) // size
        items_on_page = questions[page*size:(page+1)*size]  # Slice the list to get the items for the current page

        return ApiResponse(
            success=True,
            code=200,
            msg="Success",
            data=ResponseContent(
                content=items_on_page,
                # Pagination details
                totalPages=total_pages,
                last=page >= total_pages - 1,
                totalElements=total_items,
                first=page == 0,
                size=size,
                number=page,
                numberOfElements=len(items_on_page),
                empty=len(items_on_page) == 0
            )
        )
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))




class VetCommentResponse(BaseModel):
    vet_comment: str
@app.post("/pet-gpt-vetcomment", response_model=VetCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_vet_comment(pet_profile: PetProfile):
    systemquestion = '''
    You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare of dogs and cats.
    Upon receiving a pet's type(cat/dog), breed, gender, age, body shape and general health comments of some areas the pet is requiring attention,
    your goal is to provide personalized, practical, actionable information and advice for pet owners.
    Refer to diagnoses and health_info in pet's profile.
    Your comments should be a very concise and well articulated summary containing 2 or 3 sentences.
    Output should be in Korean language.
    Follow strictly the style, tone and manner of the following examples (line by line) of comments templates. 
    '{{NAME}}' is placeholder for the pet's name (pet_name). 
    You must replace with the actual pet's name (in the output, we should not see {{NAME}}):
신부전은 신장의 기능이 서서히 악화되면서, 체내 독소를 없애고 전반적인 체내 균형을 유지하는 능력을 점점 잃어가는 상태를 말해요. 신장에 부담을 주지 않고, 병의 진행을 늦추며, 반려동물의 삶의 질을 높이는 것이 신부전 관리의 목표에요. 신부전 환자에게는 보통 저단백질, 저인식단을 추천해요. 신장이 체내에서 단백질 대사 산물을 제거하고 인 농도를 조절하는 역할을 하기 때문에 이런 부담을 줄여주는 것이 큰 도움이 될 수 있어요. 그리고 신장 세포의 손상을 가져올 수 있는 산화 스트레스를 최소화하는 것 또한 중요해요.
{{NAME}}는 심혈관 건강 관리에 좀 더 주의를 기울여야 해요. 7세 이상부터 아이들의 심장 질환 위험성이 조금 높아질 수 있어요. 그래서 {{NAME}}의 심장과 혈관 건강을 정기적으로 확인하고, 질병을 조기에 진단하는 게 중요해요. 수의사와 이야기해서 적절한 검진 일정을 계획하고, 필요하다면 특별한 관리나 치료를 받을 수 있도록 해야 해요. 또한, {{NAME}}의 심혈관 건강을 유지하는 데 있어서 바른 식단이 중요한 역할을 해요. 고지방, 고염분 음식은 피하고, 심장에 좋은 지방산과 필수 영양소가 골고루 들어간 사료와 영양제를 선택해야 해요.
{{NAME}}은 구강 건강 관리에 좀 더 주의를 기울여야 해요. 치석은 구강 건강뿐만 아니라, 심장, 신장, 간 등의 다른 신체 부위로 세균이나 염증을 퍼뜨려 질병을 일으킬 수도 있기 때문에 매우 신경 써야 하는 문제예요. 구강 질환은 초기에는 명확한 증상이 나타나지 않을 수 있으니, {{NAME}}의 입 안을 주기적으로 확인하고 이상이 있을 경우 수의사와 상의하시는 게 좋아요. 강아지 전용 칫솔과 치약을 사용하여 주 3회 이상의 양치가 권장되고 칫솔질에 익숙하지 않을 경우 거부할 수 있으니 천천히 익숙하게 해주는 게 중요해요.
    skip mentionning supplements elements like 영양소인 오메가-3 지방산, 코엔자임 Q10, 아르기닌, 타우린, 항산화제, 비타민 B-복합체 because you will generate in another API.
'''
    payload = {
        "model": GPT4DEFAULT,#"gpt-4",  # or another model name as appropriate
        "messages": [
            {"role": "system", "content": systemquestion},
            {"role": "user", "content": f"The pet's name is {pet_profile.pet_name}. It is {pet_profile.pet_type}, breed is {pet_profile.breed}, age is {pet_profile.age}. {pet_profile.diagnoses} 내용 요약해줘요."
            }
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "OpenAI-Organization": f"{OPENAI_ORG}",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": f"{OPENAI_PROJ}"
    }

    logger.info(f"payload:{payload}")
    logger.info(f"headers:{headers}")
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(OPENAI_API_URL, json=payload, headers=headers) as response:
            if response.status != 200:
                raise HTTPException(status_code=response.status, detail="Error calling OpenAI API")
            result = await response.json()
            template = result['choices'][0]['message']['content']
            formatted_string = template.replace("{{NAME}}", pet_profile.pet_name)

    return VetCommentResponse(vet_comment=formatted_string)
    
@app.post("/pet-gpt-vetcomment-supplements", response_model=VetCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_vet_comment(pet_profile: PetProfile):
    systemquestion = '''
    You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare of dogs and cats.
    Upon receiving a pet's type(cat/dog), breed, gender, age, body shape and general health comments of some areas the pet is requiring attention,
    your goal is to provide personalized, practical, actionable information and advice for pet owners.
    you should refer to supplements in pet's profile.
    Follow strictly the style, tone and manner of the following examples of comments templates. 
    Output should be in Korean language.
    '{{NAME}}' is placeholder for the pet's name (pet_name). 
    Your comments should be a very concise and well articulated summary of 1 paragraph containing at most 3 sentences about '이퀄' supplements brand.
    You must replace with the actual pet's name (in the output, we should not see {{NAME}}):
    - 개와 고양이도 사람과 마찬가지로 나이가 들면서 눈의 망막과 수정체의 기능이 저하 돼요. 그렇기 때문에 망막 건강에 도움이 되는 루테인, 지아잔틴, 비타민 E 등 항산화 보충제를 섭취해주면, {{NAME}}의 눈이 가진 다양한 기능을 보존하고 개선하는 데 효과적일 수 있어요.
    - 피부 건강에 유익한 비타민 A와 E는 효과는 탁월하지만, 지용성 비타민이라 과다 복용하면 신체에 누적되어 악영향을 줄 수 있어요. 그래서 이퀄 피부 건강 영양제는 최적의 함량으로 최고의 효과를 기대할 수 있도록, 반려동물의 영양 성분 가이드라인을 제시하는 미국사료협회(AAFCO)와 유럽반려동물산업연합(FEDIAF)에서 권장하는 안전한 복용량에 맞추어 설계했어요. 이와 더불어 피부 세포의 재생과 회복을 돕는 아연도 조합되어 있어 {{NAME}}의 피부에 큰 도움이 될 수 있어요.
    - 이퀄 소화기 건강 영양제는 소화기 전반을 건강하게 유지하는 데 도움을 줄 수 있도록 설계했어요. 유익균의 먹이가 되는 식이섬유와 소화를 돕는 효소뿐만 아니라, 건강한 신진대사와 위장관 내 음식물의 분해를 도울 수 있는 비타민 B9과 B12도 함께 담았어요.
    - 이퀄 치아 건강 영양제에는 미국수의치과협회(VOHC)가 인정한 유일한 치아 및 구강 건강 증진 성분인 아스코필럼 노도섬과 천연 항염증제인 프로폴리스, 구강 면역력 증진에 도움을 줄 수 있는 베타글루칸을 {{NAME}}에게 딱 필요한 만큼 조합하여 담았어요.
    - 이퀄 긴장 완화 영양제에는 행복 호르몬인 세로토닌의 전구체인 L-트립토판 성분과 함께 스트레스 완화에 좋은 L-테아닌, 락티움, GABA 성분이 적절한 조합으로 담겨있어요. {{NAME}}의 식단에 긴장 완화 성분을 더해주시는 것은 어떨까요?
    - 이퀄 호흡기 건강 영양제로 {{NAME}}의 식단에 호흡기 건강에 도움이 되는 퀘르세틴을 더해주세요. 2022년 유럽의 연구진이 발표한 논문에 따르면, 퀘르세틴은 항균, 항바이러스, 항염증 효과가 뛰어나고 특히 호흡기 질환에 강력한 효과가 있는 항산화제예요. 이러한 장점 덕분에 사람의 COVID-19에서도 그 효과를 주목받기도 했어요. 강아지와 고양이에서도 염증을 감소시키고 자극을 유발하는 히스타민의 방출을 억제하는 데 도움이 된다는 보고가 있어요. 
    - 동물들의 뇌 기능에 큰 도움을 주는 커큐민이라는 강력한 항산화제를 알고 계신가요? 커큐민은 성분 특성상 섭취 후 대부분의 양이 체외로 배출되어 흡수율이 1%에 불과한 것으로 알려져 있어요. 그래서 이퀄 뇌 건강 영양제에는 이러한 점을 개선한 하이드로커큐민을 사용하여 커큐민의 흡수율을 높였어요. {{NAME}}의 뇌 건강을 위하여 식단에 커큐민을 보충해 보시는 것은 어떨까요?
    - 2022년 발표된 독일 연구진의 논문에 따르면 강아지 중 약 14%, 고양이 중 약 12~19%의 아이들이 일생에 한 번 이상 비뇨기계 질환을 겪는다고 해요. 일반적으로 비뇨기 질환은 재발률이 높기 때문에 증상이 없을 때도 세심한 관리가 필요해요. 이퀄 비뇨기 건강 영양제에 들어있는 N-아세틸-글루코사민은 비뇨기 점막 내벽의 면역력을 높이는 데 도움을 주고, 비타민B6(피리독신)는 결석의 위험을 조금이나마 줄이는 데 도움을 줄 수 있어요.
    - 항산화제는 체내에서 노화를 촉진하는 활성 산소를 제거하여 세포 손상을 예방해 줘요. 이는 질병 예방뿐만 아니라 {{NAME}}의 건강 전반에 도움이 될 수 있어요. 이퀄 항산화 영양제로 {{NAME}}의 식탁에 건강을 더해주세요. 
    - 비타민 B 복합체는 세포 단위의 에너지 생성부터 건강한 적혈구 형성, 건강한 신경 기능에 이르기까지 다양한 효과를 발휘해요. 특히, 간 질환이나 노화로 간의 기능이 약화되어있을 경우, 비타민 B를 보충해주는 것이 중요해요. 이퀄 비타민 B 영양제로 {{NAME}}의 식단에 건강을 더해보세요. 
    - 이퀄의 유산균 영양제에는 위산과 담즙산, 열을 견디고 장까지 도달하는 유효균만을 선별하여 담았어요. 이 유산균들은 다수의 연구와 논문에서 과학적으로 검증되었어요.
    
    Don't forget to generate only up to 3 sentences.
'''
    payload = {
        "model": GPT4DEFAULT,#"gpt-3.5-turbo-0125", #"gpt-4",  # Specify the correct model
        "messages": [
            {"role": "system", "content": systemquestion},
            {"role": "user", "content": f"The pet's name is {pet_profile.pet_name}, type is {pet_profile.pet_type}, breed is {pet_profile.breed}, age is {pet_profile.age}. {pet_profile.supplements} 내용 요약해줘요."}
        ]
    }
    headers = {
        "Content-Type": "application/json",
        "OpenAI-Organization": f"{OPENAI_ORG}",
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "OpenAI-Project": f"{OPENAI_PROJ}"
    }

    # Use aiohttp to make asynchronous HTTP requests
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
        async with session.post(OPENAI_API_URL, json=payload, headers=headers) as response:
            if response.status != 200:
                logger.error(f"Error calling OpenAI API: {response.status}")
                raise HTTPException(status_code=response.status, detail="Error calling OpenAI API")
            result = await response.json()
            template = result['choices'][0]['message']['content']
            formatted_string = template.replace("{{NAME}}", pet_profile.pet_name)

    return VetCommentResponse(vet_comment=formatted_string)

import socket
import requests
# Function to get the EC2 instance IP
# Function to get the EC2 instance IP using IMDSv2
def get_ec2_instance_ip():
    try:
        # Get the token
        token_response = requests.put(
            'http://169.254.169.254/latest/api/token',
            headers={'X-aws-ec2-metadata-token-ttl-seconds': '21600'}
        )
        token_response.raise_for_status()
        token = token_response.text

        # Use the token to get the instance IP
        ip_response = requests.get(
            'http://169.254.169.254/latest/meta-data/local-ipv4',
            headers={'X-aws-ec2-metadata-token': token}
        )
        ip_response.raise_for_status()
        return ip_response.text
    except requests.RequestException as e:
        logger.error(f"Error fetching EC2 instance IP: {e}")
        raise

    
async def register_with_eureka():
    if PREFIXURL == "/petgpt-service":
        # Asynchronously register service with Eureka
        # IP_ADDRESS = get_ec2_instance_ip()
        # PORT = int(os.getenv('PORT', 10070))  # Read the port from the environment variable
        # try:
        #     logger.debug(f"Registering with Eureka at {EUREKA}...")
        #     await eureka_client.init_async(eureka_server=EUREKA,
        #                                 app_name="petgpt-service",
        #                                 instance_host=IP_ADDRESS,
        #                                 instance_port=PORT)
        #     logger.info(f"Registration with Eureka successful with IP: {IP_ADDRESS} and port {PORT}")    
        # except Exception as e:
        #     logger.error(f"Failed to register with Eureka: {e}")
        #     raise HTTPException(status_code=500, detail="Failed to register with Eureka")
        # Asynchronously register service with Eureka
        try:
            logger.debug(f"Registering with Eureka at {EUREKA}...")
            await eureka_client.init_async(eureka_server=EUREKA,
                                        app_name="petgpt-service",
                                        instance_port=PORT)
            logger.info("Registration with Eureka successful.")
        except Exception as e:
            logger.error(f"Failed to register with Eureka: {e}")
        
from generation import (
    generation_websocket_endpoint_chatgpt
)
app.websocket("/ws/generation/{pet_id}")(generation_websocket_endpoint_chatgpt)

@app.on_event("startup")
async def startup_event():
    logger.setLevel(LOGGING_LEVEL)
    # Register with Eureka when the FastAPI app starts
    PORT = int(os.getenv('PORT', 10070))  # Read the port from the environment variable
    logger.info(f"Application startup: Registering PetGPT service on port {PORT} with Eureka at {EUREKA} and logging level: {LOGGING_LEVEL}")
    await register_with_eureka()
    logger.info(f"Application startup: Registering PetGPT done")

@app.get("/categories/", response_model=ApiResponse[List[dict]])
async def get_categories(pet_id: int, page: int = Query(0, ge=0), size: int = Query(3, ge=1)):
    try:
        if pet_id == -1:
            pet_name = 'no_name'
            pet_type = 'dog'
        else:
            pet_profile = petProfileRetriever.get_pet_profile(pet_id)

            pet_name = pet_profile.pet_name
            pet_type = pet_profile.pet_type

        categories = contentRetriever.get_categories(pet_type=pet_type, pet_name=pet_name)  # Assume this returns all categories as List[str]
        
        total_items = len(categories)
        total_pages = (total_items + size - 1) // size
        start = page * size
        end = start + size
        page_items = categories[start:end]

        response_content = ResponseContent(
            content=page_items,
            totalPages=total_pages,
            last=page >= total_pages - 1,
            totalElements=total_items,
            first=page == 0,
            size=size,
            number=page,
            numberOfElements=len(page_items),
            empty=len(page_items) == 0
        )

        return ApiResponse(
            success=True,
            code=200,
            msg="Success",
            data=response_content
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/document", response_model=ContentItem)
async def get_document(doc_id: int=Query(77, ge=77)):
    try:
        doc_ = contentRetriever.get_document(doc_id=doc_id)
        return ContentItem(doc_id= doc_['doc_id'], title=doc_['title'], content=doc_['content'], 
                           image_url=doc_['image_url'], link_url=doc_['link_url'], tag=doc_['tag'],
                           filter='', use_filter=False)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))    

@app.get("/contents/", response_model=ApiResponse[List[ContentItem]])
async def get_contents(query: str, pet_id: int, tags: Optional[List[str]] = Query(None),  page: int = 0, size: int = 3):
    logger.debug('get_contents : {}'.format(query))
    # Assuming the 'tags' parameter can accept a list of strings
    # Convert query params to the format expected by your content retriever
    try:
        tags_list = []

        if pet_id == -1:
            pet_type = 'dog'
        else:
            pet_profile = petProfileRetriever.get_pet_profile(pet_id)
            pet_type = pet_profile.pet_type

            if tags:
                for tag in tags:
                    if len(tag)>0:
                        tags_list.append(tag)
                
            logger.info(f"tags_list: {tags_list}")
            
        content_items = contentRetriever.get_query_contents(query=query, pet_type=pet_type, tags=tags_list)

        #if len(content_items) < 2 and pet_type != None: # No result or One result
        #    content_items = contentRetriever.get_contents(query=query) # Query without pet_type, tags

        # Calculate total number of items and pages
        total_items = len(content_items)
        total_pages = (total_items + size - 1) // size  # Compute total number of pages

        # Calculate the starting and ending index of the items for the current page
        start_index = page * size
        end_index = start_index + size
        page_items = content_items[start_index:end_index]  # Slice the list to get only the items for this page

        # Determine if this is the last page
        is_last = page == total_pages - 1
        #sort_info = SortInfo(unsorted=True, sorted=False, empty=True)

        response_content = ResponseContent(
            content=page_items,
            totalPages=total_pages,
            last=is_last,
            totalElements=total_items,
            first=page == 0,
            size=size,
            number=page,
            numberOfElements=len(page_items),
            #sort=sort_info,
            empty=len(page_items) == 0
        )

        response = ApiResponse(
            success=True,
            code=200,
            msg="Success",
            data=response_content
        )
        
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/bookmark", response_model=ApiResponse)
async def set_bookmark(user_id: int, content_id: int):
    # Placeholder for bookmarking logic
    logger.debug('set bookmark')
    try:
        doc = contentRetriever.get_document(doc_id=content_id)
        if doc['doc_id'] == str(content_id):
            ret = bookmark_set(user_id=user_id, doc_id=content_id, title=doc['title'], content=doc['content'], image_url=doc['image_url'], source_url=doc['source_url'], link_url=doc['link_url'])
        else:
            ret = False

        if ret == True:
            return ApiResponse(
                success=ret,
                code=200,
                msg="Successfully Set bookmark"
            )
        else:
            return ApiResponse(
                success=ret,
                code=500,
                msg="Can not set bookmark"              
            )

        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    #return BookmarkResponse(success=True)

@app.get("/check_bookmark", response_model=ApiResponse)
async def check_bookmark(user_id: int, content_id:int):
    logger.debug('check bookmark')
    try:
        ret = bookmark_check(user_id=user_id, doc_id=content_id)
        if ret == True:
            return ApiResponse(success=True,
                code=200,
                msg="Content is in bookmark",
            )
        else:
            return ApiResponse(
                success=False,
                code=200,
                msg="Content is not in bookmark",
            )    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/bookmark", response_model=ApiResponse[List[BookmarkItem]])
async def get_bookmarks(user_id: int, page: int = 0, size: int = 1):
    logger.debug('get_bookmarks')
    try:
        bookmarks = []
        results = bookmarks_get(user_id=user_id)
        # result => list
        for result in results:
            bookmarks.append(BookmarkItem(user_id=result['user_id'], content_id=result['doc_id'], title=result['title'], summary=result['summary'], image_url=result['image_url'], source_url=result['source_url'], link_url=result['link_url']))
        
        # Pagination logic
        total_items = len(bookmarks)
        total_pages = (total_items + size - 1) // size
        items_on_page = bookmarks[page*size:(page+1)*size]

        response_content = ResponseContent(
            content=items_on_page,
            totalPages=total_pages,
            last=page >= total_pages - 1,
            totalElements=total_items,
            first=page == 0,
            size=size,
            number=page,
            numberOfElements=len(items_on_page),
            empty=len(items_on_page) == 0
        )
        
        return ApiResponse(
            success=True,
            code=200,
            msg="Successfully get bookmarks",
            data=response_content
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/bookmark", response_model=ApiResponse)
async def delete_bookmark(user_id: str, content_id:str):
    logger.debug('delete bookmark')
    try:
        ret = bookmark_delete(user_id=user_id, doc_id=content_id)
        if ret == True:
            return ApiResponse(success=True,
            code=200,
            msg="Successfully delete bookmark",
            )
        else:
            return ApiResponse(
                success=False,
                code=500,
                msg="Can not delete bookmark",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/get-pet-profile/{pet_id}", response_model=PetProfile)
async def get_pet_profile(pet_id: int):
    pet_profile = petProfileRetriever.get_pet_profile(pet_id)

    if pet_profile:
        # Create and return a PetProfile instance
        logger.debug(f"pet_profile: {pet_profile}")
        return pet_profile
    else:
        logger.error(f"Pet profile not found for pet_id: {pet_id}")
        raise HTTPException(status_code=404, detail="Pet profile not found")

if __name__ == "__main__":
    import uvicorn
    PORT = 9090
    logger.info(f"Starting server on port {PORT} with Eureka server: {EUREKA}")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, workers=4, log_level="debug")
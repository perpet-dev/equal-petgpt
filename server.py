# -*- coding: utf-8 -*-
from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi import WebSocket, WebSocketDisconnect
from fastapi import File, UploadFile, status
import uvicorn
import requests
from pydantic import BaseModel, HttpUrl
from pydantic.generics import GenericModel
from typing import Generic, TypeVar, List, Optional
from config import PORT, EUREKA, MONGODB

import os
import openai
import base64
from openai import OpenAI
import openai
from openai import OpenAI
import uuid

from py_eureka_client import eureka_client
from config import PORT, EUREKA, LOGGING_LEVEL, OPENAI_EMBEDDING_MODEL_NAME, OPENAI_EMBEDDING_DIMENSION, PINECONE_API_KEY, PINECONE_INDEX
from pinecone import Pinecone, ServerlessSpec, PodSpec
import pprint
from petprofile import PetProfile
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
app = FastAPI(root_path=prefix)
#app = FastAPI()
# # Allow all origins
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],  # Allows all origins
#     allow_credentials=True,
#     allow_methods=["*"],  # Allows all methods
#     allow_headers=["*"],  # Allows all headers
# )
# static files directory for web app
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

@app.get("/petgpt", response_class=HTMLResponse)
async def healthreport(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "query_params": request.query_params})

# Models for input validation and serialization

class ContentItem(BaseModel):
    doc_id:str
    title: str
    content: str
    image_url: HttpUrl
    link_url: HttpUrl
    tag: List[str] = []

class CategoryItem(BaseModel):
    category_sn: str
    category_title: str
    content: List[ContentItem]

class ContentRequest(BaseModel):
    content: str


# Define a type variable for the GenericModel
T = TypeVar('T')
# class SortInfo(BaseModel):
#     unsorted: bool
#     sorted: bool
#     empty: bool

# class Pageable(BaseModel):
#     sort: SortInfo
#     pageNumber: int
#     pageSize: int
#     offset: int
#     paged: bool
#     unpaged: bool

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
    data: ResponseContent[T]

class BookmarkResponse(BaseModel):
    success: bool

class QuestionItem(BaseModel):
    title: str
    question_id: str

class PetGPTQuestionListResponse(BaseModel):
    list: List[QuestionItem]
    
@app.post("/process-pet-image")
async def process_pet_images(pet_name: str, petImages: List[UploadFile] = File(...)):

    petgpt_system_imagemessage = '''
    You are 'PetGPT', a friendly and enthusiastic GPT that specializes in analyzing images of dogs and cats. \
    Upon receiving an image, you try to identify the pet's type, breed and age. \
    If you get the name of the pet, please incorporate it into your answer. \
    type=dog or cat, breed=breed of the pet, age=age of the pet \
    Output strictly as a JSON object containing the fields: answer, name, type, breed, age ." \
For age, you must use the following categories:
푸릇푸릇 폭풍 성장기"
생기 넘치는 청년기
꽃처럼 활짝 핀 중년기
성숙함이 돋보이는
우리집 최고 어르신
and type should be either 'dog' or 'cat'.

For breeds refer to the following list:
name	type
골든 리트리버	dog
그레이 하운드	dog
그레이트 데인	dog
그레이트 스위스 마운틴 독	dog
그레이트 피레니즈	dog
그리폰 브뤼셀	dog
꼬똥 드 툴레아	dog
노르웨이 룬트훈트	dog
노르웨이안 엘크하운드	dog
노르웨이안 하운드	dog
노리치 테리어	dog
노바 스코셔 덕 톨링 레트리버	dog
뉴펀들랜드 독	dog
닥스훈트	dog
달마시안	dog
더치 셰퍼드 독	dog
도고 아르헨티노	dog
도그 드 보르도	dog
도베르만	dog
디어하운드	dog
래브라도 리트리버	dog
라사압소	dog
러시안 블랙 테리어	dog
러시안-유러피안 라이카	dog
로디지안 리지백	dog
루마니안 셰퍼드	dog
로첸	dog
로트와일러	dog
잉글리쉬 마스티프	dog
타트라 마운틴 쉽독	dog
나폴리탄 마스티프	dog
말티즈	dog
말티푸	dog
맨체스터 테리어	dog
멕시칸 헤어리스 독	dog
무디	dog
미니어처 슈나우저	dog
미니어처 핀셔	dog
프렌치 포인팅 독	dog
믹스견	dog
바바리안 마운틴 하운드	dog
바베트	dog
바센지	dog
바셋 블뢰 드 가스코뉴	dog
바셋 포브 드 브르타뉴	dog
바셋하운드	dog
버니즈 마운틴 독	dog
벌고 포인팅 독	dog
베들링턴 테리어	dog
베르가마스코 셰퍼드 독	dog
벨지안 그리폰	dog
벨지안 셰퍼드 독	dog
보더 콜리	dog
보더 테리어	dog
보르조이	dog
보스 쉽독	dog
보스턴 테리어	dog
복서	dog
볼로네즈	dog
불 테리어	dog
불독	dog
불마스티프	dog
네바 마스커레이드	cat
노르웨이 숲	cat
데본렉스	cat
돈스코이	cat
라가머핀	cat
라팜	cat
렉돌	cat
러시안 블루	cat
맹크스 (Manx)	cat
먼치킨	cat
메인쿤	cat
믹스묘	cat
발리니즈	cat
버만	cat
버미즈	cat
버밀라	cat
벵갈	cat
봄베이	cat
브리티쉬 롱헤어	cat
브리티쉬 숏헤어	cat
사바나	cat
샤르트뢰	cat
샴	cat
세이셸루아	cat
셀커크 렉스	cat
소말리	cat
스노우슈	cat
스코티시 스트레이트	cat
스코티시 폴드	cat
스핑크스	cat
시베리안	cat
싱가푸라	cat
아메리칸 밥테일	cat
아메리칸 숏헤어	cat
아메리칸 와이어헤어	cat
아메리칸 컬	cat
아비시니안	cat
엑조틱 숏헤어	cat
오리엔탈	cat
오스트레일리안 미스트	cat
오시캣	cat
이집션 마우	cat
재패니즈 밥테일	cat
카오 마니	cat
코니시 렉스	cat
코랏	cat
코리안 숏헤어	cat
쿠릴리안 밥테일	cat
킴릭	cat
타이	cat
터키쉬 반	cat
터키쉬 앙고라	cat
통키니즈	cat
페르시안	cat
피터볼드	cat
픽시 밥	cat
하바나 브라운	cat
브라질리언 테리어	dog
브리아드	dog
브리타니 스파니엘	dog
블랙 앤 탄 쿤하운드	dog
블러드 하운드	dog
비글	dog
비숑 프리제	dog
비어디드 콜리	dog
쁘띠 바셋 그리폰 방뎅	dog
쁘띠 브라반숑	dog
샤를로스 울프하운드	dog
사모예드	dog
살루키	dog
샤페이	dog
서식스 스파니엘	dog
세인트 버나드	dog
세인트 저먼 포인터	dog
셰틀랜드 쉽독	dog
슈나우저	dog
스위스 하운드	dog
스카이 테리어	dog
스코티시 테리어	dog
스키퍼키	dog
스타포드셔 불 테리어	dog
스테비훈	dog
스패니시 그레이하운드	dog
스패니시 마스티프	dog
스패니시 워터 독	dog
스패니시 하운드	dog
스피츠	dog
슬로바키안 하운드	dog
슬루기	dog
시바	dog
시베리안 허스키	dog
시츄	dog
시코쿠	dog
실리엄 테리어	dog
아르투아 하운드	dog
아리에쥬아	dog
아메리칸 스태퍼드셔 테리어	dog
아메리칸 아키타	dog
아메리칸 워터 스파니엘	dog
아메리칸 코카 스파니엘	dog
아메리칸 폭스하운드	dog
아이리시 글렌 오브 이말 테리어	dog
아이리시 세터	dog
아이리시 소프트코티드 휘튼 테리어	dog
아이리시 울프하운드	dog
아이리시 워터 스파니엘	dog
아이리시 테리어	dog
아이슬랜드 쉽독	dog
아키타	dog
아펜핀셔	dog
아프간 하운드	dog
알라스칸 말라뮤트	dog
에어데일 테리어	dog
오스트레일리안 셰퍼드	dog
오스트레일리안 스텀피 테일 캐틀 독	dog
오스트레일리안 켈피	dog
오스트레일리안 테리어	dog
오스트리안 블랙 앤드 탄 하운드	dog
오스트리안 핀셔	dog
오터 하운드	dog
올드 대니시 포인팅 독	dog
올드 잉글리시 쉽독	dog
와이마라너	dog
요크셔테리어	dog
시베리안 라이카	dog
웨스트 하일랜드 화이트 테리어	dog
웰시 스프링어 스파니엘	dog
웰시 코기	dog
웰시 테리어	dog
이탈리안 그레이하운드	dog
이탈리안 볼피노	dog
이탈리안 포인팅 독	dog
잉글리시 세터 (르웰린)	dog
잉글리시 스프링거 스파니엘	dog
잉글리시 코커 스파니엘	dog
잉글리시 토이 테리어 블랙 앤드 탠	dog
잉글리시 포인터	dog
잉글리시 폭스하운드	dog
자이언트 슈나우저	dog
재패니즈 스피츠	dog
재패니즈 친	dog
재패니즈 테리어	dog
잭 러셀 테리어	dog
저먼 롱헤어드 포인팅 독	dog
저먼 셰퍼드	dog
저먼 쇼트-헤어드 포인팅 독	dog
저먼 스파니엘	dog
저먼 핀셔	dog
저먼 하운드	dog
진돗개	dog
차우차우	dog
차이니스 크레스티드	dog
체서피크 베이 리트리버	dog
체스키 테리어	dog
치와와	dog
카네코르소	dog
카디건 웰시 코기	dog
카발리에 킹 찰스 스파니엘	dog
캉갈 셰퍼드 독	dog
커릴리언 베어 독	dog
컬리 코티드 리트리버	dog
케리 블루 테리어	dog
케언 테리어	dog
케이넌 독	dog
그린란드견	dog
빠삐용 (콘티넨탈 토이 스파니엘)	dog
러프 콜리	dog
스무스 콜리	dog
코몬도르	dog
쿠바츠	dog
쿠이커혼제	dog
크로아티안 셰퍼드 독	dog
크롬폴란데	dog
클럼버 스파니엘	dog
킹 찰스 스파니엘	dog
타이 리지백	dog
타이완 독	dog
티베탄 스파니엘	dog
티베탄 마스티프	dog
티베탄 테리어	dog
파라오 하운드	dog
파슨 러셀 테리어	dog
퍼그	dog
페키니즈	dog
펨브록 웰시 코기	dog
포르투기즈 쉽독	dog
포르투기즈 워터 독	dog
포르투기즈 포인팅 독	dog
포메라니안	dog
폭스 테리어	dog
폴리시 로랜드 쉽독	dog
폴리시 하운드	dog
푸델포인터	dog
푸들	dog
프렌치 불독	dog
프렌치 스파니엘	dog
프렌치 하운드	dog
플랫 코티드 리트리버	dog
피니쉬 하운드	dog
피니시 스피츠	dog
피레니안 마스티프	dog
피레니안 마운틴 독	dog
피레니안 셰펴드	dog
피레니안 쉽독	dog
비즐라 (헝가리안 포인터)	dog
헝가리안 그레이하운드	dog
호바와트	dog
홋카이도견	dog
화이트 스위스 셰퍼드 독	dog
갈갈	dog
갈갈	dog
골든	dog
골든	dog
휘핏	dog
토이푸들	dog
포메러니안	dog
말티숑	dog
요크셔테리어	dog
미니어처 푸들	dog
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
@app.get("/pet-knowledge-list/{pet_id}", response_model=ApiResponse[List[CategoryItem]])
async def pet_knowledge_list(pet_id: str, page: int = Query(1, ge=1), items_per_page: int = Query(10, ge=1)):

    list = []
    retriever = PetProfileRetriever()
    pet_profile = retriever.get_pet_profile(pet_id)
    retriever.close()

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

class BannerItem(BaseModel):
    #배너 링크 url
    link_url: HttpUrl
    #배너 이미지
    image_url: HttpUrl

# class BannerResponse(BaseModel):
#     total_page: int
#     list: List[BannerItem]
#메인 배너 리스트
@app.get("/main-banner-list", response_model=ApiResponse[List[BannerItem]])
async def main_banner_list(page: int = Query(0, ge=0), size: int = Query(5, ge=1)):
    banners = [
        BannerItem(link_url="https://example1.com", image_url="https://example1.com/image.jpg"),
        BannerItem(link_url="https://example2.com", image_url="https://example2.com/image.jpg"),
        BannerItem(link_url="https://example3.com", image_url="https://example3.com/image.jpg"),
        BannerItem(link_url="https://example4.com", image_url="https://example4.com/image.jpg"),
        BannerItem(link_url="https://example5.com", image_url="https://example5.com/image.jpg")
    ]

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

@app.get("/pet-gpt-question-list/{pet_id}", response_model=ApiResponse[List[QuestionItem]])
async def pet_gpt_question_list(pet_id: str, page: int = Query(0, ge=0), size: int = Query(3, ge=1)):

    logger.debug(f"PetGPT Service for pet_id: {pet_id}")
    # Dummy data
    questions = [
        QuestionItem(title="How often should I feed my pet?", question_id="Q1"),
        QuestionItem(title="What is the best diet for a pet like mine?", question_id="Q2"),
        QuestionItem(title="How to manage my pet's anxiety?", question_id="Q3"),
        QuestionItem(title="How often should I feed my pet?", question_id="Q4"),
        QuestionItem(title="What is the best diet for a pet like mine?", question_id="Q5"),
        QuestionItem(title="How to manage my pet's anxiety?", question_id="Q6"),
        QuestionItem(title="How often should I feed my pet?", question_id="Q7"),
        QuestionItem(title="What is the best diet for a pet like mine?", question_id="Q8"),
        QuestionItem(title="How to manage my pet's anxiety?", question_id="Q9"),
        QuestionItem(title="How often should I feed my pet?", question_id="Q10")
    ]
    
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


class VetCommentResponse(BaseModel):
    vet_comment: str
@app.post("/pet-gpt-vetcomment", response_model=VetCommentResponse, status_code=status.HTTP_201_CREATED)
async def create_vet_comment(pet_profile: PetProfile):
    systemquestion = '''
    You are 'PetGPT', a friendly and enthusiastic GPT that specializes in healthcare of dogs and cats.
    Upon receiving a pet's type(cat/dog), breed, gender, age, body shape and general health comments of some areas the pet is requiring attention,
    your goal is to provide personalized, practical, actionable information and advice for pet owners.
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
# 내분비계는 우리 몸의 다양한 기능들, 예를 들어 대사, 성장, 수면 등을 조절하는 여러 가지 호르몬을 분비해요. 내분비계 질환이 생기면, 호르몬의 불균형이 발생해 몸의 정상적인 기능을 방해하고, 이로 인해 산화 스트레스가 일어날 수 있어요. 예를 들어, 쿠싱증후군에서 스트레스 호르몬인 코르티솔이 과도하게 분비되면, 면역 체계의 기능을 약화시키고 감염과 염증에 노출될 위험을 증가시킬 수 있어요. 또한, 갑상선 호르몬이 부족하면, 세포의 에너지 생산이 줄어들고 이는 미토콘드리아에서 과도한 '자유 라디칼'을 발생시킬 수 있어요. '자유 라디칼'은 세포와 DNA에 손상을 입히는 물질로, 산화 스트레스를 일으키는 주요 원인 중 하나에요. 이렇게 내분비계 질환은 여러 가지 방식으로 산화 스트레스를 일으킬 수 있어요. 그래서 내분비계 기저 질환을 가진 {{NAME}}처럼 아이들에게선 적절한 수의학적 치료와 함께 산화 스트레스를 최소화하는 방법을 고려하는 것이 중요해요.
# {{NAME}}가 비뇨기계 질환을 겪었다는 사실을 정말 안타깝게 생각해요. 7살 이상의 반려묘의 경우, 방광의 수축력이 감소할 수 있어요. 이는 소변을 완전히 비울 수 없게 하며, 방광염의 위험성을 증가 시켜요. 그래서 주기적인 배뇨 훈련을 통해 방광을 완전히 비울 수 있도록 도와야 해요. 또한 충분히 물을 마실 수 있게 하고, 소변의 적정 pH를 유지하기 위해 올바른 식단을 제공하는 것이 중요해요. 많은 물을 마시면 소변이 묽어지고, 자주 소변을 볼 수 있어서, 방광을 깨끗하게 유지하는데 도움이 되거든요. 결석의 종류에 따라 다르지만 대체적으로 소변의 pH는 약 6.0-6.5를 유지하는 게 좋아요. 이를 위해 수의사와 상담을 통해 특정 비뇨기계 사료를 추천받을 수도 있어요. 칼슘은 인의 1~2배가 되도록 조절하는 것이 바람직하고요. 단백질을 많이 섭취하면 인이 급격히 올라갈 수 있으니, 평소에 육류 간식을 많이 먹지 않도록 주의해야 해요. 권장 간식과 섭취량은 수의사와 상담을 통해 결정하는 것이 좋아요. 
# 비대성 심근병증(HCM)은 고양이에서 흔히 발생하는 심장병으로, 심장 근육이 비정상적으로 두꺼워져 펌프 기능이 약화되는 질환이에요. 유전적 요인 때문에 랙돌, 브숏, 페르시안 같은 일부 품종이 더욱 취약하지만, 다른 종에서도 발생할 수 있어요. 초기 단계에서는 증상이 뚜렷하지 않지만, 점차 호흡 곤란과 식욕 부진 등이 나타날 수 있어요. 심장초음파, 혈압 측정, 흉부 X-레이 등을 통해 진단하고, Pro-BNP와 Troponin 같은 혈액 검사도 진단과 예후 평가에 도움이 돼요. 질병의 진행 정도와 증상에 따라 심부전 관리와 혈전 형성 예방을 위한 약물 치료가 필요할 수 있어요. 진단 후에는 스트레스 최소화, 식단 조절 그리고 체중 관리가 중요하고, 정기적인 검진을 통해 질병의 진행 상황을 확인하고 필요한 치료를 받아야 해요. 현재까지 완치 방법이 없지만, 적절한 관리와 치료를 통해 삶의 질을 향상시키고, 심장 부전과 같은 합병증의 발생을 예방하거나 지연시킬 수 있어요. 그래서, HCM을 조기에 진단하는 것이 매우 중요하답니다.
# 최근에 아이가 특별한 이유 없이 무기력해 보인 적이 있었나요? 무기력한 증상을 보이거나 잇몸이나 코가 촉촉하지 않고 끈적이거나 말라 있다면 탈수의 징후일 수 있어요. 수분은 매우 중요한 역할을 해요. 소화, 영양분의 흡수, 체온의 조절, 기관과 세포의 기능 유지 등 대부분의 신체 작용은 물이 존재해야만 이루어져요. 탈수 상태에서는 이러한 과정들이 제대로 작동하지 않아, 신체의 에너지 생성이 잘 되지 않고, 균형이 무너지죠. 따라서 항상 신선한 물을 제공해줘야 하고, 물을 계속 잘 마시지 않는다면 식단의 일부를 습식 사료로 변경하는 것을 고려해 보시는 것이 좋아요. 일반적으로, 중성화한 성견은 몸무게 1kg당 하루에 약 50-60ml의 물을 섭취해야 해요. 즉, 만약 아이가 5kg이라면 하루에 약 250-300ml의 물을 섭취해야 해요. 다만, 권장 음수량은 아이의 건강 상태나 활동량, 기온 등에 따라 달라질 수 있으므로 정확한 용량은 수의사와의 상담을 통해서 결정하세요.
# {{NAME}}은 피부 건강 관리에 좀 더 신경을 써야 해요. 피부 건강은 아이들이 섭취하는 영양소의 균형과 밀접한 관련이 있어요. 특히, 오메가-3 같은 필수 지방산은 피부의 수분 유지와 염증 방지에 도움을 줘요. 충분한 수분 섭취도 중요해요. 그래서 신선한 물을 언제든지 마실 수 있게 해주셔야 해요. 이 외에 레티놀, 토코페롤 등이 들어간 피부 맞춤 영양 보충제를 선택하면 도움이 될 수 있어요. 레티놀은 세포 재생을 촉진하고, 토코페롤은 항산화 작용이 탁월하며 피부의 수분 장벽을 강화하는 역할을 해요. 적절한 영양분 섭취와 더불어, 적절한 목욕 및 그루밍으로 피부를 청결하게 관리하는 것도 중요해요. 강아지의 피부 pH는 사람과 다르기 때문에 전용 샴푸를 사용해야해요. 너무 자주 목욕시키면 피부가 건조해지고 가려움증을 유발할 수 있으니, 수의사의 조언에 따라 적절한 목욕 빈도를 유지해주세요. 만약에 비정상적으로 보이는 붉은 반점, 가려움, 분비물 등의 변화가 있다면 즉시 수의사와 상의해주셔야 해요.
# 먼저, {{NAME}}의 건강을 위해 보호자님이 얼마나 신경을 쓰고 계신지 알아, 그 노력과 애정을 진심으로 응원해요. {{NAME}}의 경우 심혈관계 질환을 앓고 있다고 말씀해주셨네요. 대동맥과 좌심실을 나누는 이첨판막에 점액종성 변화가 생기는 MMVD가 소형견에서 가장 일반적으로 나타나는 심장 질환이에요. 활동량이 눈에 띄게 줄어들거나, 숨을 쉬는 데 힘들어하는 등의 증상이 보인다면 이미 심각한 응급 상황일 수 있어서 반드시 병원에 가야 해요. 아이의 일상 행동 패턴을 알고, 변화를 조기에 파악하는 것이 중요해요. 아이가 편히 잠을 잘 때, 1분 동안 몇 번 숨을 쉬는지 세는 것도 좋은 방법이에요. 정상적인 호흡 횟수는 분당 10-30회 정도이고, 이 범위를 벗어나면 문제가 있는 것으로 볼 수 있어요. 혀나 잇몸의 색깔을 주기적으로 확인하고, 분홍색이 아닌 보라색이나 회색 등으로 변했다면 전신에 산소 공급이 제대로 이루어지지 않고 있는 것을 나타낼 수 있으니, 바로 수의사와 상담해야 해요.
# {{NAME}}은 눈 건강 관리를 좀 더 세심하게 하는 것이 좋다고 판단돼요. {{NAME}}의 눈을 건강하게 유지해 줄 수 있는 주요 영양소들을 알아볼게요. 비타민 A (레티놀)는 망막의 건강을 유지하고, 백내장의 발생을 줄이는데 도움을 줄 수 있어요. 비타민 E (토코페롤)는 강력한 항산화제로 작용하여 자유 라디칼로부터 {{NAME}}의 눈을 보호하는 역할을 할 수 있어요. 오메가-3 지방산, 특히 DHA와 EPA는 망막 건강을 증진하고, 안구 건조증 증상을 완화하는 역할을 수행할 수 있어요. 루테인과 제아잔틴은 노화로 인한 시력저하를 방지할 수 있는 항산화 카로티노이드에요. 이런 영양소들이 충분히 들어있는 영양 보충제를 복용하면 {{NAME}}의 눈을 건강하게 유지하는 데 큰 도움을 줄 수 있어요. 그런데, 개인의 건강 상태에 따라 필요한 영양 성분은 다를 수 있으니 특별한 증상이 있을 경우 꼭 수의사와 상담한 후 결정하시길 바래요.
# 요즘 {{NAME}}의 기력이 없어 보이지 않았나요? 우리 {{NAME}}이 힘들어하는 것은 '산화 스트레스' 때문일 수 있다는 건 알고 계셨나요? 산화 스트레스는 몸속에 '자유 라디칼'이라는 물질이 과도하게 많아져서 발생하는데요. 이 자유 라디칼은 생명체의 정상적인 생리활동 중에도 발생하지만, 너무 많이 증가하면 세포나 조직에 손상을 주고, 여러 가지 질병을 유발하기도 해요. 주로 기저질환, 스트레스, 부적절한 식사, 환경적 요인 등으로 발생하죠. {{NAME}}처럼 10살 이상의 노령견은 일반적인 식사만으로는 충분한 항산화 성분을 공급받기 어려울 수 있어요. 수의사와의 정기적인 상담을 통해 {{NAME}}의 상태를 잘 파악하고 어떤 항산화 성분이 도움이 될 수 있는지 조언을 구해보는 게 좋아요. 이퀄에서 추천하는 대표적인 항산화제인 비타민 E(토코페롤), 셀레늄 그리고 코엔자임Q10은 함께 작용하여 산화 스트레스를 줄이고 세포 손상을 방지하는 중요한 역할을 합니다. {{NAME}}의 건강을 위해 식단에 항산화제를 추가해보는 건 어떨까요?
# 중년령 이상의 반려견은 백내장, 안구건조증 등과 같은 만성 안과 질환에 걸릴 확률이 높아요. 백내장은 수정체가 흐릿해지는 질환으로, 수정체 내의 단백질이 변형되어 덩어리를 이루고, 빛의 통과를 방해하여 시력을 잃게 만드는 거예요. 반면, 안구건조증은 눈물샘의 기능 장애나 손상 때문에 생겨나요. 안구건조증을 앓고 있는 강아지의 눈 표면은 건조해지고 통증과 충혈, 점막 손상을 일으킨답니다. 그래서 강아지가 눈을 자주 비비거나, 눈 분비물이 끈적거리는 등의 증상을 보일 수 있어요. {{NAME}}의 눈 건강을 위해 일상적인 관리가 중요해요. 눈물 자국은 눈 주변 피부에 자극을 주고 면역력을 낮출 수 있으니 매일 눈 주변을 깨끗이 유지하고 이물질이나 눈꼽은 제거해주어야 해요. 또한, 비타민 A, C, E와 오메가-3 지방산 같은 눈 건강에 좋은 영양소가 들어간 식사를 제공하는 것도 도움이 돼요. 가장 중요한 것은 정기적으로 수의사에게 안과 검진을 받아서 문제를 빨리 발견하고 적절하게 치료하는 거예요.
# 우선, {{NAME}}의 건강을 관리해주고 계신 반려인님의 애정과 노력을 진심으로 응원한다는 말씀을 드리고 싶어요. 종양이 있는 반려동물의 영양 관리는 매우 중요해요. 종양은 종종 높은 에너지 요구량을 특징으로 하거든요. 그래서 체중 유지와 근육량 소실을 예방하기 위해 고품질의 단백질 식품을 통한 영양 섭취가 필요하답니다. 면역 시스템 강화도 중요한데, 오메가-3 지방산 같은 특정 영양소가 암의 진행을 늦추는 데 도움이 될 수 있어요. 그리고 암 치료 중에는 식욕 부진, 설사, 구토 등의 부작용이 생길 수 있으므로, 이러한 증상을 완화하는 식사 방식을 고려해야 해요. 더불어 식단에 셀레늄과 비타민 E 같은 항산화제를 더해주는 것이 도움이 될 수 있으니 보충을 고려해보세요. 다만, 각각의 애완동물마다 건강 상태나 영양 필요량이 다르므로, {{NAME}}에게 맞는 식단은 반드시 수의사와 상의해서 결정하시는 것이 좋아요.
# 7살 이하의 비교적 어린 고양이라고 해도 상부 호흡기 감염, 기관지염, 천식 등 다양한 호흡기 질환에 노출될 위험이 있어요. 이런 질환들은 기침, 호흡 곤란, 식욕 부진 등의 증상을 일으킬 수 있어요. 이런 증상이 발견되면 바로 수의사에게 도움을 청해야 해요. 호흡기 질환을 예방하고 관리하는 몇 가지 방법들을 소개할게요. 상기도 감염은 주로 바이러스나 세균, 특히 고양이 헤르페스 바이러스, 칼리시 바이러스, 클라미디아 등에 의해서 발생해요. 이런 감염을 효과적으로 예방하는 방법 중 하나는 정기적인 백신 접종이에요. 또한, 고양이 스트레스를 최소화하고, 건강한 생활 습관을 유지함으로써 면역력을 강화하면 감염을 예방하는 데 도움이 돼요. 기관지염은 흡입된 자극물질에 의해 발생할 수 있어요. 이를 예방하기 위해서는 주거 환경을 청결하게 유지하고, 실내 공기의 건조함을 최소화하는 거에요. 만약 질환 증상이 발견되면 바로 수의사와 상담하여 적절한 치료를 받아야 해요.


    OPENAI_API_KEY="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"
    openai.api_key=OPENAI_API_KEY
    client = OpenAI(
        organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
    )
    completion = client.chat.completions.create(
        model="gpt-4", #"gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{systemquestion}"},
            {"role": "user", "content": f"{pet_profile}"},
        ]
    )
    template = completion.choices[0].message.content
    pet_name = pet_profile.pet_name
    formatted_string = template.replace("{{NAME}}", "{}").format(pet_name)
    logger.debug(f"vet_comment:{formatted_string}")
    return VetCommentResponse(
            vet_comment=formatted_string
        )
    
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
    OPENAI_API_KEY="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"
    openai.api_key=OPENAI_API_KEY
    client = OpenAI(
        organization='org-oMDD9ptBReP4GSSW5lMD1wv6',
    )
    completion = client.chat.completions.create(
        model="gpt-4", #"gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"{systemquestion}"},
            {"role": "user", "content": f"{pet_profile}"},
        ]
    )
    template = completion.choices[0].message.content
    pet_name = pet_profile.pet_name
    formatted_string = template.replace("{{NAME}}", "{}").format(pet_name)
    logger.debug(f"vet_comment:{formatted_string}")
    return VetCommentResponse(
            vet_comment=formatted_string
        )

async def register_with_eureka():
    if prefix == "/petgpt-service":
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

# Assuming EqualContentRetriever is defined elsewhere and imported correctly
from content_retriever import EqualContentRetriever, BREEDS_DOG_TAG, BREEDS_CAT_TAG

contentRetriever = EqualContentRetriever()
from petprofile import PetProfileRetriever
petProfileRetriever = PetProfileRetriever()


@app.get("/categories/", response_model=ApiResponse[List[dict]])
async def get_categories(pet_id: int, page: int = Query(0, ge=0), size: int = Query(3, ge=1)):
    try:
        retriever = PetProfileRetriever()
        pet_profile = retriever.get_pet_profile(pet_id)
        retriever.close()

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

@app.get("/contents/", response_model=ApiResponse[List[ContentItem]])
async def get_contents(query: str, pet_id: int, tags: Optional[List[str]] = Query(None),  page: int = 0, size: int = 3):
    # Assuming the 'tags' parameter can accept a list of strings
    # Convert query params to the format expected by your content retriever
    retriever = PetProfileRetriever()
    pet_profile = retriever.get_pet_profile(pet_id)
    retriever.close()

    pet_type = pet_profile.pet_type

    tags_list = []
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

@app.post("/bookmark-content", response_model=BookmarkResponse)
async def bookmark_content(content_id: str, auth_info: str):
    # Placeholder for bookmarking logic
    return BookmarkResponse(success=True)

@app.get("/get-pet-profile/{pet_id}", response_model=PetProfile)
async def get_pet_profile(pet_id: int):
    retriever = PetProfileRetriever()
    pet_profile = retriever.get_pet_profile(pet_id)
    retriever.close()

    if pet_profile:
        # Create and return a PetProfile instance
        print(f"pet_profile: {pet_profile}")
        return pet_profile
    else:
        raise HTTPException(status_code=404, detail="Pet profile not found")

if __name__ == "__main__":
    import uvicorn
    print(f"Starting server on port {PORT} with Eureka server: {EUREKA}")
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="debug")
#-*- coding:utf-8 -*- 
#!/usr/bin/env python
# by Albert 
import mysql.connector
import time
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec #, PodSpec
from datasets import Dataset
#import numpy as np
import json
# import pprint
# import openai
import pandas as pd
import re
import jsonlines
import random
from pymongo import MongoClient
from datetime import datetime

from subject_json import SUBJECT_JSON
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE, OPENAI_API_KEY, OPENAI_EMBEDDING_MODEL_NAME, OPENAI_EMBEDDING_DIMENSION, OPENAI_ORG, PINECONE_INDEX, PINECONE_API_KEY
from config import MONGODB, MONGODB_DBNAME

INDEX_NAME = 'equalapp-240514'
BREEDS_DOG_TAG = '62'
BREEDS_CAT_TAG = '276'
BREEDS_NONE = ''
MATCH_SCORE_CUTOFF = 0.4

from config import LOG_NAME, LOG_FILE_NAME, LOGGING_LEVEL
from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)

pc = Pinecone(PINECONE_API_KEY)
spec = ServerlessSpec(cloud='aws', region='us-west-2')  

PINECONE_SQL = "select perpet.mcard.top as category, perpet.mcard.id as id, perpet.mcard.tag, perpet.mcard.image as image , perpet.mcard.main_title as title, perpet.mcard.summary as summary,  GROUP_CONCAT(perpet.mcard_sub.sub_title SEPARATOR ' ') as sub_title,  GROUP_CONCAT(perpet.mcard_sub.text SEPARATOR ' ') as sub_text FROM perpet.mcard, perpet.mcard_sub where perpet.mcard.id = perpet.mcard_sub.mcard_id GROUP BY perpet.mcard_sub.mcard_id"
#PINECONE_SQL = "select perpet.mcard.top as category, perpet.mcard.id as id, perpet.mcard.tag, perpet.mcard.image as image , perpet.mcard.main_title as title, perpet.mcard.summary as summary,  GROUP_CONCAT(perpet.mcard_sub.sub_title SEPARATOR ' ') as sub_title,  GROUP_CONCAT(perpet.mcard_sub.text SEPARATOR ' ') as sub_text FROM perpet.mcard, perpet.mcard_sub where perpet.mcard.id > 481 and  perpet.mcard.id = perpet.mcard_sub.mcard_id GROUP BY perpet.mcard_sub.mcard_id"

class EqualContentRetriever():
    # Singleton 으로 구성
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):         
            cls._instance = super().__new__(cls) 
        return cls._instance 
    
    def __init__(self, index_name=INDEX_NAME):
        cls = type(self)
        if not hasattr(cls, "_init"):
            logger.debug('EqualContentRetriever::init')
            self.index_name = index_name
            self.contents_cache = []
            # MongoDB setup
            
            mongodb_connection_string = MONGODB
            database_name = MONGODB_DBNAME 
            mclient = MongoClient(mongodb_connection_string)
            mongo_db = mclient[database_name]
            self.subjects_collection = mongo_db["knowlege_subject"]
            self.questions_collection = mongo_db["questions"]

            ###### OPEN AI ########
            self.openai_client = OpenAI(
                api_key = OPENAI_API_KEY,
                organization=OPENAI_ORG,
            )
            
            #self.category_dict = json.loads(SUBJECT_JSON)
            #self.__put_subjects_to_mongo()
            #self.__put_question_json_to_mongo()
            self.question_map = {}
            self.__load_questions_from_mongo()
            #self.__load_questions_jsonl()
            
            self.category_dict = self.__load_subjects_from_mongo()
            self.__category_content_cache()
            self.__load_breed_map()
                        
            cls._init = True

    def __put_subjects_to_mongo(self):
        # put subject json from mongodb
        logger.debug("EqualContentRetriever::__load_subject_json")

        data = {
            'subjects':json.dumps(json.loads(SUBJECT_JSON), ensure_ascii=False), 
            'time_stamp': datetime.now()
        }
        try:
            self.subjects_collection.insert_one(data)
        except Exception as e:
            logger.error(f"An error occurred: {e}")

    def __load_subjects_from_mongo(self):
        # load subject json from mongodb
        logger.debug("EqualContentRetriever::__load_subject_json")

        try:
            subject_json = self.subjects_collection.find()
            return json.loads(subject_json[0]['subjects'])
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return None

    def __put_question_json_to_mongo(self):
        logger.debug("EqualContentRetriever::__put_question_json_to_mongo")
        with jsonlines.open("questions.jsonl") as jsonl_f:
            for line in jsonl_f.iter():
                # put mongo db 
                logger.debug(line['question'])
                self.questions_collection.insert_one(line)

    def __load_questions_from_mongo(self):
        logger.debug("EqualContentRetriever::__load_questions_from_mongo")
        questions = self.questions_collection.find()
        self.question_map.clear()
        for question in questions:
            key_ = "{}_{}".format(question['type'], question['breed'].replace(' ', ''))
            if key_ in self.question_map:
                self.question_map[key_] = self.question_map[key_] + '\n' + question['question']
            else:
                self.question_map[key_] = question['question']

    def __load_breed_map(self):
       logger.debug("EqualContentRetriever::__load_breed_map")
       self.breed_map = pd.read_csv('breed.tag.map', sep='\t', header=0)

    def __load_questions_jsonl(self):
        # {"doc_id": 390, "type": "dog", "breed_tag": 489, "breed_id": 74, "breed": "비글", "question": "비글은 고집이 강한 개인가요?"}
        logger.debug("EqualContentRetriever::__load_question_jsonl")
        with jsonlines.open("questions.jsonl") as jsonl_f:
            for line in jsonl_f.iter():
                key_ = "{}_{}".format(line['type'], line['breed'].replace(' ', ''))
                if key_ in self.question_map:
                    self.question_map[key_] = self.question_map[key_] + '\n' + line['question']
                else:
                    self.question_map[key_] = line['question']

    def __generate_questions(self, system_question:str, content_to_analyze:str):
        logger.debug('EqualContentRetriever::__generate_questions')
        #client = OpenAI(
        #    api_key = OPENAI_API_KEY,
        #    organization=OPENAI_ORG,
        #)
        
        completion = self.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",#,"gpt-4", 
            messages=[
                {"role": "system", "content": f"{system_question}"},
                {"role": "user", "content": f"Here is the content: {content_to_analyze}"},
            ]
        )
        logger.debug(completion.choices[0].message)
        return completion.choices[0].message.content

    def __category_content_cache(self):
        logger.debug('EqualContentRetriever::__category_content_cache')

        index = pc.Index(INDEX_NAME)
        for x in self.category_dict:
            if x['type'] == 'dog' or x['type'] == 'cat':
                elements = []
                for y in x['curations']:
                    doc_id = y['doc_id']
                    filters = y['filter']
                    use_filter = y['use_filter']
                    ret = index.query(
                            id=str(doc_id),
                            top_k=1, 
                            include_metadata=True)
                    if len(ret['matches']) > 0:
                        if len(filters) == 0: # filter 없음
                            elements.append({
                                            'doc_id':ret['matches'][0]['id'],
                                            'title':ret['matches'][0]['metadata']['title'], 
                                            'content':ret['matches'][0]['metadata']['content'],
                                            'image_url':ret['matches'][0]['metadata']['image_url'],
                                            'source_url':ret['matches'][0]['metadata']['source_url'],
                                            'link_url':ret['matches'][0]['metadata']['link_url'],
                                            'tag':ret['matches'][0]['metadata']['tag'], 
                                            'filter':'', 
                                            'use_filter':use_filter
                                        })
                        else:
                            for filter in filters:
                                elements.append({
                                            'doc_id':ret['matches'][0]['id'],
                                            'title':ret['matches'][0]['metadata']['title'], 
                                            'content':ret['matches'][0]['metadata']['content'],
                                            'image_url':ret['matches'][0]['metadata']['image_url'],
                                            'source_url':ret['matches'][0]['metadata']['source_url'],
                                            'link_url':ret['matches'][0]['metadata']['link_url'],
                                            'tag':ret['matches'][0]['metadata']['tag'], 
                                            'filter': str(filter),
                                            'use_filter':use_filter
                                        })

                self.contents_cache.append({'pet_type':x['type'],'category_sn':x['sn'], 'category_title':x['subject'] ,'content':elements})
                
    def __pinecone_index(self, text_dataset:Dataset, dimension=OPENAI_EMBEDDING_DIMENSION, incremental=True):   
        logger.debug('EqualContentRetriever::__pinecone_index')
        
        existing_indexes = [ index_info['name']  for index_info in pc.list_indexes() ]

        if incremental == False:
            if self.index_name in existing_indexes:
                print('Delete index : {}'.format(self.index_name))
                pc.delete_index(self.index_name)
                time.sleep(1)
                existing_indexes = [ index_info['name']  for index_info in pc.list_indexes() ]

        if self.index_name not in existing_indexes: # not found
            logger.debug('Create index : {}'.format(self.index_name))
            pc.create_index(
                self.index_name, 
                dimension = dimension, 
                metric='cosine', 
                spec=spec)

        # wait for index to be initialized
        while not pc.describe_index(self.index_name).status['ready']:
            time.sleep()

        index = pc.Index(self.index_name)
        
        # indexing
        count = 0
        batch_size = 32

        for i in tqdm(range(0, len(text_dataset['content']), batch_size)):
            # set end position of batch
            i_end = min(i+batch_size, len(text_dataset['content']))
            # get batch of lines and IDs
            lines_batch = text_dataset['content'][i: i+batch_size]
            ids_batch = text_dataset['id'][i: i+batch_size]
            source_batch = text_dataset['source_url'][i:i+batch_size]
            link_batch = text_dataset['link_url'][i:i+batch_size]
            images_batch = text_dataset['image_url'][i:i+batch_size]
            tags_batch = text_dataset['tag'][i:i+batch_size]
            titles_batch = text_dataset['title'][i:i+batch_size]
            categories_batch = text_dataset['category'][i:i+batch_size]
            res = self.openai_client.embeddings.create(input=lines_batch, model=OPENAI_EMBEDDING_MODEL_NAME) # create embeddings
            embeds = [record.embedding for record in res.data]
            meta = [{'category': categories_batch[n], 'title':titles_batch[n], 'tag':tags_batch[n], 'content': lines_batch[n], 'source_url':source_batch[n], 'link_url':link_batch[n],'image_url':images_batch[n]} for n in range(0, len(categories_batch))] # prep metadata and upsert batch
            to_upsert = zip(ids_batch, embeds, meta)
            index.upsert(vectors=list(to_upsert)) # upsert to Pinecone

    def __pinecone_search(self, index_name, query, filter=None, top_k=5, include_metadata=True):
        logger.debug('EqualContentRetriever::__pinecone_search => {}, {}'.format(query, filter))
        
        result = []
        filter_only = False
        if query == '': 
            query = ' '
            filter_only = True

        xq = self.openai_client.embeddings.create(input=query, model=OPENAI_EMBEDDING_MODEL_NAME).data[0].embedding
        index = pc.Index(index_name)
        
        ret = index.query(
            vector=[xq],
            filter=filter, 
            top_k=top_k, include_metadata=include_metadata)
        ###
        #if filter_only:
            # sort by filter 
            # 빠르게 정렬할 방법 찾아야 함.
        #    print('')
        ###
        for res in ret['matches']:
            if res['score'] >= MATCH_SCORE_CUTOFF:
                result.append({
                                'doc_id':res['id'], 
                                'title':res['metadata']['title'], 
                                'content':res['metadata']['content'], 
                                'image_url':res['metadata']['image_url'], 
                                'source_url':res['metadata']['source_url'],
                                'link_url':res['metadata']['link_url'], 
                                'tag':res['metadata']['tag']
                                })
        return result

    def get_document(self, doc_id:int):
        logger.debug('EqualContentRetriever::get_document => {}'.format(doc_id))
        index = pc.Index(INDEX_NAME)
        ret = index.query(
                    id=str(doc_id),
                    top_k=1, 
                    include_metadata=True)
        if len(ret['matches']) > 0:
            return {
                'doc_id':ret['matches'][0]['id'],
                'title':ret['matches'][0]['metadata']['title'], 
                'content':ret['matches'][0]['metadata']['content'],
                'image_url':ret['matches'][0]['metadata']['image_url'],
                'source_url':ret['matches'][0]['metadata']['source_url'],
                'link_url':ret['matches'][0]['metadata']['link_url'],
                'tag':ret['matches'][0]['metadata']['tag'], 
            }
        else:
            return {}
        
    
        
    def get_random_questions(self, pet_type:str, breed:str='', top_n=3):
        logger.debug('EqualContentRetriever::get_random_questions => {}, {}'.format(pet_type, breed))
        
        breed_question = ''
        use_breed = False
        breed = breed.replace(' ', '')
        selected_questions = []
        type_key = "{}_".format(pet_type)
        type_questions = self.question_map[type_key].split('\n')
        
        if breed == '': # no breed
            if len(type_questions) >= top_n:
                selected_questions = random.sample(type_questions, top_n)
            else:
                logger.critical('Qustion list not enough...')
                selected_questions = type_questions
        else: # breed           
            breed_key = "{}_{}".format(pet_type, breed)
            if breed_key in self.question_map:
                breed_questions = self.question_map[breed_key].split('\n')
                if len(breed_questions) >= 1:
                    breed_question = random.sample(breed_questions, 1) # 질문 1개 (breed 맞춤)
                selected_questions = breed_question + random.sample(type_questions, top_n - 1) 
            else: 
                logger.critical("Check Breed Key : {}".format(breed_key))
                selected_questions = random.sample(type_questions, top_n)

        logger.debug('>> random questions : {}'.format(selected_questions))
        return selected_questions
    
    def build_question_jsonl(self, db_host=DB_HOST, db_port=DB_PORT, db_user=DB_USER, db_password=DB_PASSWORD, db_database=DB_DATABASE):
        logger.info("EqualContentRetiever::build_pinecone_index")
        # Step 1 : Iterate content db
        # Step 2 : Extract Question From content
        # Step 3 : Generate Question JSONL file
        jsonl_file_name = 'questions.jsonl'
        sql = "select perpet.mcard.id as id, perpet.mcard.tag as tag, perpet.mcard.main_title as title, perpet.mcard.summary as summary, GROUP_CONCAT(perpet.mcard_sub.sub_title SEPARATOR ' ') as sub_title,  GROUP_CONCAT(perpet.mcard_sub.text SEPARATOR ' ') as sub_text FROM perpet.mcard, perpet.mcard_sub where perpet.mcard.id = perpet.mcard_sub.mcard_id GROUP BY perpet.mcard_sub.mcard_id"

        # Establishing a connection to MariaDB
        connection = mysql.connector.connect(
                        host=db_host,
                        user=db_user,
                        password=db_password,
                        database=db_database, 
                        port=db_port
                    )
        # Creating a cursor object
        cursor = connection.cursor()
        cursor.execute(sql)
        res = cursor.fetchall()
        system_question = '''Hello, I'm compiling an FAQ section for a pet care website and need to extract potential frequently asked questions \
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

        for row in tqdm(res):
            id = row[0]
            tags = []
            types = []
            tags_ = row[1].split(',')
            
            for tag in tags_:
                tag = tag.strip()
                if len(tag) > 0:
                    if len(tag) > 0 and int(tag) in self.breed_map['tag_id'].values: 
                        tags.append(int(tag)) 
                    elif tag == BREEDS_DOG_TAG:
                        types.append('dog')
                    elif tag == BREEDS_CAT_TAG:
                        types.append('cat')
            
            if len(types) == 0:
                types.append('nobreeds')                

            content = "{} {} {} {}".format(row[2], row[3], row[4], row[5])
            questions = self.__generate_questions(system_question, content)
            questions = questions.split('\n')
            # Add original document question
            questions.append(row[2])
            # Remove duplicate question
            questions_key = dict.fromkeys(questions)
            questions = list(questions_key)

            with open(jsonl_file_name, '+a', encoding='utf-8') as jsonl_file:
                for question in questions:
                    # { "doc_id": 2, "type":"dog", "breeds":"234", "questions":""}, 
                    
                    question = re.sub('^-', '', question)
                    question = re.sub('^\d+.', '', question)
                    question = re.sub('^\d+', '', question)
                    
                    question = question.strip()


                    if len(question) > 0:
                        for type in types:
                            if len(tags) == 0:
                                element = {'doc_id':id, 'type':type, 'breed_tag':-1, 'breed_id':-1, 'breed': '', 'question': question}
                                json.dump(element, jsonl_file, ensure_ascii=False)
                                jsonl_file.write('\n')
                            else:
                                for tag_ in tags:
                                    breed_id = int(self.breed_map.loc[self.breed_map['tag_id'] == tag_]['breed_id'].values[0])
                                    breed = self.breed_map.loc[self.breed_map['tag_id'] == tag_]['name'].values[0]
                                    element = {'doc_id':id, 'type':type, 'breed_tag':tag_, 'breed_id':breed_id, 'breed': breed, 'question': question}
                                    json.dump(element, jsonl_file, ensure_ascii=False)
                                    jsonl_file.write('\n')
                jsonl_file.flush()
            jsonl_file.close()

    def build_pincone_index(self, db_host=DB_HOST, db_port=DB_PORT, db_user=DB_USER, db_password = DB_PASSWORD, db_database=DB_DATABASE):
        logger.info("EqualContentRetiever::build_pinecone_index")
        # Establishing a connection to MariaDB
        connection = mysql.connector.connect(
                        host=db_host,
                        user=db_user,
                        password=db_password,
                        database=db_database, 
                        port=db_port
                    )
        # Creating a cursor object
        cursor = connection.cursor()

        sql = PINECONE_SQL
        cursor.execute(sql)
        result = cursor.fetchall()
        categories, ids, tags, titles, images, contents, sources, links = [], [], [], [], [], [], [], []

        logger.info(">>> Total row to index : {}".format(len(result)))

        for row in result:
            categories.append(row[0])
            ids.append(str(row[1]))
            tags.append([x for x in row[2].split(',') if x])
            images.append(row[3])
            titles.append(row[4])
            contents.append(' '.join(row[6:]).replace('\n',' '))
            sources.append('https://equal.pet/content/ViewApp/{}'.format(row[1]))
            links.append('https://equal.pet/content/View/{}'.format(row[1]))

        data_dict = {'category':categories, 'id': ids, 'tag':tags, 'title':titles, 'content':contents, 'source_url':sources, 'link_url': links, 'image_url':images}
        text_dataset = Dataset.from_dict(data_dict)
        self.__pinecone_index(text_dataset=text_dataset)

    def get_categories(self, pet_type:str, pet_name:str):
        logger.debug("EqualContentRetriever::get_categories")
        categories = []
        for x in self.category_dict:
            if pet_type == x['type']:
                subject = x['subject']
                subject = subject.replace('{petName}', "{{{}}}".format(pet_name))
                categories.append({'sn':x['sn'], 'subject':subject})        
        return categories 

    def get_category_contents(self, pet_type:str, sn:str, tags:list=[int]):    
        logger.debug("EqualContentRetriever::get_category_contents")
        tags = list(filter(None, tags))
        selected_contents = []
        for x in self.contents_cache:
            if x['pet_type'] == pet_type and x['category_sn'] == sn:
                for content in x['content']:
                    if content['use_filter'] == True:
                        for tag in tags:
                            if tag in content['filter']:
                                selected_contents.append(content)
                    else:
                        selected_contents.append(content)
                #return x['content']
        return selected_contents

    def get_query_contents(self, query:str, pet_type:str='', tags:list=[]):
        # Pinecone search
        logger.debug("EqualContentRetriever::get_query_contents, query={}, pet_type={}, tags={}".format(query, pet_type, tags))
        tag_filter = []
        filter_elem = []
                
        if pet_type == 'dog':
            filter_elem.append({"tag":{"$in":[BREEDS_DOG_TAG]}})
        elif pet_type == 'cat':
            filter_elem.append({"tag":{"$in":[BREEDS_CAT_TAG]}})
        
        if len(tags) > 0:
            for tag in tags:
                tag_filter.append({"tag":tag})
            filter_elem.append({"$or":tag_filter})

        filter_elem_cnt = len(filter_elem)

        if filter_elem_cnt >= 2:
            filter = {
                "$and": filter_elem
            }
            result = self.__pinecone_search(self.index_name, query, filter)            
        elif filter_elem_cnt == 1:
            filter = filter_elem[0]
            result = self.__pinecone_search(self.index_name, query, filter)
        else:
            result = self.__pinecone_search(self.index_name, query)
        return result    

if __name__ == "__main__":
    db_host = "127.0.0.1" # 
    db_user = "perpetapi" # 
    db_password = "O7dOQFXQ1PYY" # 
    db_database = "perpet"
    db_port = 3307

    contentRetriever = EqualContentRetriever()

    def test_question():
        questions = [
            "고양이가 이물을 섭식했을 때의 증상은 무엇인가요?",
            "고양이가 이물을 삼키면 어떻게 대처해야 하나요?",
            "이물 섭식으로 인한 긴급 상황 시 대처 방안은?",
            "이물을 자주 먹는 고양이 보호자를 위한 팁?",
            "이물을 섭식한 고양이가 있을 때 주의해야 할 사항은 무엇인가요?",
            "고양이 이물 섭식을 예방하기 위해 보호자가 취할 수 있는 조치는 무엇인가요?",
            "우리 고양이가 이물을 꿀꺽 삼켜버렸어요!",
            "어떤 종류의 강아지 사료가 있으며 각각의 장단점은 무엇인가요?",
            "건사료는 어떤 장점과 단점을 가지고 있나요?",
            "습식사료는 어떤 장점과 단점을 가지고 있나요?",
            "홈메이드 사료를 주는 것의 장단점은 무엇인가요?",
            "생식(raw) 사료를 선택할 때 주의할 점은 무엇인가요?",
            "화식을 주는 것의 장단점은 무엇인가요?",
            "어떤 사료를 선택해야 하는지 결정하는 데 도움을 받는 방법은 무엇인가요?",
            "사료를 선택할 때 주의해야 할 점은 무엇인가요?",
            "우리 아이는 어떤 사료가 가장 잘 맞을까?",
        ]

        for question in questions:
            ret = contentRetriever.question_related_to_nutrients(question)
            logger.debug('{}:{}'.format(question, ret))

    #test_question()

    #contentRetriever.build_pincone_index(db_host=db_host, db_port=db_port, db_user=db_user, db_password=db_password, db_database=db_database)
    #contentRetriever.build_question_jsonl(db_host=db_host, db_port=db_port, db_user=db_user, db_password=db_password, db_database=db_database)
    
    def random_question():
        result = contentRetriever.get_random_questions('cat', '메인 쿤')
        logger.debug(result)
        result = contentRetriever.get_random_questions('cat')
        logger.debug(result)
        result = contentRetriever.get_random_questions('dog')
        logger.debug(result)
        contentRetriever.get_category_contents(pet_type='dog', )

    def tag_dump():
        sql = "select perpet.tag.id, perpet.tag.name as name from perpet.tag order by id"

        # Establishing a connection to MariaDB
        connection = mysql.connector.connect(
                        host=db_host,
                        user=db_user,
                        password=db_password,
                        database=db_database, 
                        port=db_port
                    )
        # Creating a cursor object
        cursor = connection.cursor()
        cursor.execute(sql)
        res = cursor.fetchall()

        with open('tags.tsv', 'w', encoding='utf-8') as output_file:
            for row in res:
                output_file.write("{}\t{}\n".format(row[0], row[1]))
                

    def test_categories():
        ret = contentRetriever.get_categories(breeds=BREEDS_DOG_TAG, pet_name='뽀삐')
        logger.debug(ret)
        
    # print('-'* 80)
    
    # ret = contentRetriever.get_contents2(breeds=BREEDS_DOG_TAG, sn='DG011V2-01', tags=[])
    # # ret = contentRetriever.get_contents(query='', category='의학 정보', tags=['276', '65'])
    # print(ret)
    
    #ret = contentRetriever.get_contents(query='', breeds= BREEDS_DOG_TAG, category='반려 생활')
    #print(ret)
    # print('-'* 80)

    # ret = contentRetriever.get_contents(query='', breeds= BREEDS_CAT_TAG, category='반려 생활')
    # pprint.pprint(ret, indent=4)
    # print('-'* 80)

    # ret = contentRetriever.get_contents(query='예방접종 어떻게 해요?', breeds=BREEDS_DOG_TAG)
    # pprint.pprint(ret)
   
    #contentRetriever.build_index()
    # #ret = contentRetriever.get_contents2(breeds=BREEDS_DOG_TAG, sn='DG011V2-01', tags=[])
    # #print(ret)
    #tag_dump()

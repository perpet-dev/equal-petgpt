import mysql.connector
import time
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec, PodSpec
from datasets import Dataset
import numpy as np
import json
import pprint
from subject_json import SUBJECT_JSON

OPENAI_API_KEY = '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'
OPENAI_EMBEDDING_MODEL_NAME = 'text-embedding-3-small'
OPENAI_EMBEDDING_DIMENSION = 1536
PINECONE_API_KEY =  'dcce7d00-5f7f-48bf-8b19-33480e74ad12'
DB_HOST =  "127.0.0.1" # "dev.promptinsight.ai"  
DB_USER = "perpetapi" # "perpetdev" #  
DB_PASSWORD = "O7dOQFXQ1PYY" #"perpet1234!" #  # 
DB_DATABASE = "perpet"
DB_PORT = 3307
INDEX_NAME = 'equalapp2'
BREEDS_DOG_TAG = '62'
BREEDS_CAT_TAG = '276'
BREEDS_NONE = ''
MATCH_SCORE_CUTOFF = 0.4

client = OpenAI(api_key = OPENAI_API_KEY)
pc = Pinecone(PINECONE_API_KEY)
spec = ServerlessSpec(cloud='aws', region='us-west-2')  


class EqualContentRetriever():
    def __init__(self, index_name=INDEX_NAME):
        self.index_name = index_name
        self.category_dict = json.loads(SUBJECT_JSON)
        self.contents_cache = []
        self.__category_content_cache()

    def __category_content_cache(self):
        # make content cache for performance
        index = pc.Index(INDEX_NAME)
        for x in self.category_dict:
            if x['type'] == 'dog' or x['type'] == 'cat':
                elements = []
                for y in x['curations']:
                    doc_id = y['doc_id']
                    ret = index.query(
                            id=str(doc_id),
                            top_k=1, 
                            include_metadata=True)
                    if len(ret['matches']) > 0:
                        elements.append({
                                        'doc_id':ret['matches'][0]['id'],
                                        'title':ret['matches'][0]['metadata']['title'], 
                                        'content':ret['matches'][0]['metadata']['content'],
                                        'image_url':ret['matches'][0]['metadata']['image_url'],
                                        'link_url':ret['matches'][0]['metadata']['source_url'],
                                        'tag':ret['matches'][0]['metadata']['tag']
                                    })
                self.contents_cache.append({'pet_type':x['type'],'category_sn':x['sn'], 'category_title':x['subject'] ,'content':elements})
                
    def __pinecone_index(self, text_dataset:Dataset, dimension=OPENAI_EMBEDDING_DIMENSION, incremental=True):   
        existing_indexes = [ index_info['name']  for index_info in pc.list_indexes() ]

        if incremental == False:
            if self.index_name in existing_indexes:
                print('Delete index : {}'.format(self.index_name))
                pc.delete_index(self.index_name)
                time.sleep(1)
                existing_indexes = [ index_info['name']  for index_info in pc.list_indexes() ]

        if self.index_name not in existing_indexes: # not found
            print('Create index : {}'.format(self.index_name))
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
            images_batch = text_dataset['image_url'][i:i+batch_size]
            tags_batch = text_dataset['tag'][i:i+batch_size]
            titles_batch = text_dataset['title'][i:i+batch_size]
            categories_batch = text_dataset['category'][i:i+batch_size]
            res = client.embeddings.create(input=lines_batch, model=OPENAI_EMBEDDING_MODEL_NAME) # create embeddings
            embeds = [record.embedding for record in res.data]
            meta = [{'category': categories_batch[n], 'title':titles_batch[n], 'tag':tags_batch[n], 'content': lines_batch[n], 'source_url':source_batch[n], 'image_url':images_batch[n]} for n in range(0, len(categories_batch))] # prep metadata and upsert batch
            to_upsert = zip(ids_batch, embeds, meta)
            index.upsert(vectors=list(to_upsert)) # upsert to Pinecone

    def __pinecone_search(self, index_name, query, filter=None, top_k=5, include_metadata=True):
        result = []
        filter_only = False
        if query == '': 
            query = ' '
            filter_only = True

        xq = client.embeddings.create(input=query, model=OPENAI_EMBEDDING_MODEL_NAME).data[0].embedding
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
            #result.append({'category':res['metadata']['category'], 'title':res['metadata']['title'], 'content':res['metadata']['content'], 'image_url':res['metadata']['image_url'], 'link_url':res['metadata']['source_url'], 'tag':res['metadata']['tag']})
            if res['score'] >= MATCH_SCORE_CUTOFF:
                result.append({'doc_id':res['id'], 
                            'title':res['metadata']['title'], 
                            'content':res['metadata']['content'], 
                            'image_url':res['metadata']['image_url'], 
                            'link_url':res['metadata']['source_url'], 
                            'tag':res['metadata']['tag']})
        return result

    def build_index(self, db_host=DB_HOST, db_port=DB_PORT, db_user=DB_USER, db_password = DB_PASSWORD, db_database=DB_DATABASE):
        # Establishing a connection to MariaDB
        self.connection = mysql.connector.connect(
                        host=db_host,
                        user=db_user,
                        password=db_password,
                        database=db_database, 
                        port=db_port
                    )
        # Creating a cursor object
        self.cursor = self.connection.cursor()

        sql = "select perpet.mcard.top as category, perpet.mcard.id as id, perpet.mcard.tag, perpet.mcard.image as image , perpet.mcard.main_title as title, perpet.mcard.summary as summary,  GROUP_CONCAT(perpet.mcard_sub.sub_title SEPARATOR ' ') as sub_title,  GROUP_CONCAT(perpet.mcard_sub.text SEPARATOR ' ') as sub_text FROM perpet.mcard, perpet.mcard_sub where perpet.mcard.id = perpet.mcard_sub.mcard_id GROUP BY perpet.mcard_sub.mcard_id"
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        categories, ids, tags, titles, images, contents, sources = [], [], [], [], [], [], []

        for row in result:
            categories.append(row[0])
            ids.append(str(row[1]))
            tags.append([x for x in row[2].split(',') if x])
            images.append(row[3])
            titles.append(row[4])
            contents.append(' '.join(row[4:]).replace('\n',' '))
            sources.append('https://equal.pet/content/View/{}'.format(row[1]))

        data_dict = {'category':categories, 'id': ids, 'tag':tags, 'title':titles, 'content':contents, 'source_url':sources, 'image_url':images}
        text_dataset = Dataset.from_dict(data_dict)
        self.__pinecone_index(text_dataset=text_dataset)

    def get_categories(self, pet_type:str, pet_name:str):
        categories = []
        for x in self.category_dict:
            if pet_type == x['type']:
                subject = x['subject']
                subject = subject.replace('{petName}', "{{{}}}".format(pet_name))
                categories.append({'sn':x['sn'], 'subject':subject})        
        return categories 

    # def get_categories(self):
    #     categories = []
    #     sql = "select top from perpet.mcard group by top"
    #     self.cursor.execute(sql)
    #     result = self.cursor.fetchall()
    #     for row in result:
    #         categories.append(row[0].strip())
    #     return json.dumps({'category':categories}, ensure_ascii=False)


    def get_category_contents(self, pet_type:str, sn:str, tags:list=[int]):    
        for x in self.contents_cache:
            if x['pet_type'] == pet_type and x['category_sn'] == sn:
                return x['content']
    
    def get_query_contents(self, query:str, pet_type:str='', tags:list=[]):
        # Pinecone search
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
    contentRetriever = EqualContentRetriever()
    
   
    # ret = contentRetriever.get_categories2(breeds=BREEDS_DOG_TAG, pet_name='뽀삐')
    # pprint.pprint(ret, indent=4)
        
    # print('-'* 80)
    
    # ret = contentRetriever.get_contents2(breeds=BREEDS_DOG_TAG, sn='DG011V2-01', tags=[])
    # # ret = contentRetriever.get_contents(query='', category='의학 정보', tags=['276', '65'])
    # print(ret)
    
    # ret = contentRetriever.get_contents(query='', breeds= BREEDS_DOG_TAG, category='반려 생활')
    # pprint.pprint(ret, indent=4)
    # print('-'* 80)

    # ret = contentRetriever.get_contents(query='', breeds= BREEDS_CAT_TAG, category='반려 생활')
    # pprint.pprint(ret, indent=4)
    # print('-'* 80)

    # ret = contentRetriever.get_contents(query='예방접종 어떻게 해요?', breeds=BREEDS_DOG_TAG)
    # pprint.pprint(ret)
   
    # #contentRetriever.build_index()
    # #ret = contentRetriever.get_contents2(breeds=BREEDS_DOG_TAG, sn='DG011V2-01', tags=[])
    # #print(ret)
import mysql.connector
import time
from tqdm import tqdm
from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec, PodSpec
from datasets import Dataset
import numpy as np
import json
import pprint

OPENAI_API_KEY = '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'
OPENAI_EMBEDDING_MODEL_NAME = 'text-embedding-3-small'
OPENAI_EMBEDDING_DIMENSION = 1536
PINECONE_API_KEY =  'dcce7d00-5f7f-48bf-8b19-33480e74ad12'
INDEX_NAME = 'equalapp2'
BREEDS_DOG_TAG = '62'
BREEDS_CAT_TAG = '276'
BREEDS_NONE = ''

from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE

client = OpenAI(api_key = OPENAI_API_KEY)
pc = Pinecone(PINECONE_API_KEY)
spec = ServerlessSpec(cloud='aws', region='us-west-2')  

class EqualContentRetriever():
    def __init__(self, index_name=INDEX_NAME, db_host=DB_HOST, db_port=DB_PORT, db_user=DB_USER, db_password = DB_PASSWORD, db_database=DB_DATABASE):
        print('EqualContentRetriever')
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
        self.index_name = index_name

    def build_index(self):
        sql = "select perpet.mcard.top as category, perpet.mcard.id as id, perpet.mcard.tag, perpet.mcard.image as image , perpet.mcard.main_title as title, perpet.mcard.summary as summary,  GROUP_CONCAT(perpet.mcard_sub.sub_title SEPARATOR ' ') as sub_title,  GROUP_CONCAT(perpet.mcard_sub.text SEPARATOR ' ') as sub_text FROM perpet.mcard, perpet.mcard_sub where perpet.mcard.id = perpet.mcard_sub.mcard_id GROUP BY perpet.mcard_sub.mcard_id"
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        categories, ids, tags, titles, images, contents, sources = [], [], [], [], [], [], []

        for row in result:
            categories.append(row[0])
            ids.append(row[1])
            tags.append([x for x in row[2].split(',') if x])
            images.append(row[3])
            titles.append(row[4])
            contents.append(' '.join(row[4:]).replace('\n',' '))
            sources.append('https://equal.pet/content/View/{}'.format(row[1]))

        data_dict = {'category':categories, 'id': ids, 'tag':tags, 'title':titles, 'content':contents, 'source_url':sources, 'image_url':images}
        text_dataset = Dataset.from_dict(data_dict)
        self.pinecone_index(text_dataset=text_dataset)


    def get_categories(self):
        categories = []
        sql = "select `top` from perpet.mcard group by top"
        self.cursor.execute(sql)
        result = self.cursor.fetchall()
        for row in result:
            categories.append(row[0].strip())
        return categories #json.dumps({'category':categories}, ensure_ascii=False)

    def pinecone_index(self, text_dataset:Dataset, dimension=OPENAI_EMBEDDING_DIMENSION, incremental=True):   
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
            ids_batch = [str(n) for n in range(i, i_end)]
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

    def pinecone_search(self, index_name, query, filter=None, top_k=10, include_metadata=True):
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
        #print(res)
        #if filter_only:
            # sort by filter 
            # 빠르게 정렬할 방법 찾아야 함.
        #    print('')
        ###
        for res in ret['matches']:
            result.append({'category':res['metadata']['category'], 'title':res['metadata']['title'], 'image_url':res['metadata']['image_url'], 'link_url':res['metadata']['source_url'], 'tag':res['metadata']['tag']})
        return result #json.dumps(result, ensure_ascii=False)

    def get_contents(self, query, breeds:str=BREEDS_NONE, category:str='', tags:list=[]):
        # Pinecone search
        tag_filter = []
        filter_elem = []
        
        if category != '':
            print('category:', category)
            filter_elem.append({"category": {"$eq":category}})
        
        if breeds == BREEDS_DOG_TAG or breeds == BREEDS_CAT_TAG:
            print('pet_type:', breeds)
            filter_elem.append({"tag":{"$in":[breeds]}})
    
        if tags is not None and len(tags) > 0:
            for tag in tags:
                print('tag:', tag)
                tag_filter.append({"tag":tag})
            filter_elem.append({"$or":tag_filter})

        filter_elem_cnt = len(filter_elem)

        if filter_elem_cnt >= 2:
            filter = {
                "$and": filter_elem
            }
            result = self.pinecone_search(self.index_name, query, filter)            
        elif filter_elem_cnt == 1:
            filter = filter_elem[0]
            result = self.pinecone_search(self.index_name, query, filter)
        else:
            result = self.pinecone_search(self.index_name, query)
            print(result)
        return result    

if __name__ == "__main__":
    contentRetriever = EqualContentRetriever()
    ret = contentRetriever.get_categories()
    # pprint.pprint(ret, indent=4)
    # print('-'* 80)
    # ret = contentRetriever.get_contents(query='', category='의학 정보', tags=['276', '65'])
    # print(ret)
    ret = contentRetriever.get_contents(query='', breeds= BREEDS_DOG_TAG, category='반려 생활', tags=['276'])
    pprint.pprint(ret, indent=4)
    print('-'* 80)

    ret = contentRetriever.get_contents(query='', breeds= BREEDS_CAT_TAG, category='반려 생활')
    # pprint.pprint(ret, indent=4)
    # print('-'* 80)

    ret = contentRetriever.get_contents(query='예방접종 어떻게 해요?', breeds= BREEDS_CAT_TAG)
    pprint.pprint(ret)
    
    #contentRetriever.build_index()
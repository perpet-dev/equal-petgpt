#-*- coding:utf-8 -*- 
#!/usr/bin/env python
# by Albert 
from pymongo import MongoClient
from datetime import datetime
from config import MONGODB
from config import LOG_NAME, LOG_FILE_NAME, LOGGING_LEVEL
from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)

# MongoDB setup
client = MongoClient(MONGODB)
mongo_db = client.perpet_healthcheck
bookmark_collection = mongo_db["bookmarks"]

def set_bookmark(user_id:int, content_id:int):
    logger.debug('set_bookmark')
    data = {"user_id":user_id, "content_id":content_id}
    result = bookmark_collection.count_documents(data)
    if result == 0: # 없음
        bookmark_collection.insert_one(data)
    return True

def get_bookmarks(user_id:int):
    logger.debug('get_bookmarks')
    results = bookmark_collection.find(filter={"user_id":user_id})
    return list(results)

def delete_bookmarks(user_id:int, content_id:int):
    logger.debug('delete_bookmarks')
    data = {"user_id":user_id, "content_id":content_id}
    result = bookmark_collection.delete_one(data)
    return result.acknowledged

if __name__ == "__main__":
    set_bookmark(user_id=223, content_id=150)
    set_bookmark(user_id=223, content_id=154)
    set_bookmark(user_id=223, content_id=157)
    set_bookmark(user_id=13, content_id=144)
    set_bookmark(user_id=13, content_id=142)
    set_bookmark(user_id=13, content_id=132)
    
    print(get_bookmarks(user_id=223))
    print(get_bookmarks(user_id=13))

    delete_bookmarks(user_id=13, content_id=142)
    print(get_bookmarks(user_id=13))

    delete_bookmarks(user_id=223, content_id=150)
    print(get_bookmarks(user_id=223))
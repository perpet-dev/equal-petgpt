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

def bookmark_set(user_id:int, doc_id:int, title:str, content:str, image_url:str, link_url:str):
    logger.debug('set_bookmark')
    summary = content[:50]
    data = {
                "user_id":user_id, 
                "doc_id":doc_id, 
                "title":title, 
                "summary":summary, 
                "image_url":image_url, 
                "link_url":link_url, 
                "time_stamp": datetime.now()
            }
    result = bookmark_collection.count_documents({"user_id":user_id, "doc_id":doc_id})
    if result == 0: # 없음
        bookmark_collection.insert_one(data)
    return True

def bookmarks_get(user_id:int):
    logger.debug('get_bookmarks')
    results = bookmark_collection.find(filter={"user_id":user_id})
    return list(results)

def bookmark_delete(user_id:int, doc_id:int):
    logger.debug('delete_bookmarks')
    data = {"user_id":int(user_id), "doc_id":int(doc_id)}
    result = bookmark_collection.delete_one(data)
    logger.debug("result : {}".format(result))
    return bool(result.acknowledged)


if __name__ == "__main__":
    bookmark_set(user_id=223, doc_id=150, title="제목", content="본문본문ggksjgdsljflsdjflds dsfjsdf ldsfjfdsl jfslkdsfjldfsjdsfjkldfsjlfsd ldfsj lfdslfdsj lfjdlfdsl jdfsl f jldsjfslfjdslfj slfds", image_url='', link_url='')
    bookmark_set(user_id=223, doc_id=154, title="제목", content="본문본문ggksjgdsljflsdjflds dsfjsdf ldsfjfdsl jfslkdsfjldfsjdsfjkldfsjlfsd ldfsj lfdslfdsj lfjdlfdsl jdfsl f jldsjfslfjdslfj slfds", image_url='', link_url='')
    bookmark_set(user_id=223, doc_id=157, title="제목", content="본문본문ggksjgdsljflsdjflds dsfjsdf ldsfjfdsl jfslkdsfjldfsjdsfjkldfsjlfsd ldfsj lfdslfdsj lfjdlfdsl jdfsl f jldsjfslfjdslfj slfds", image_url='', link_url='')
    bookmark_set(user_id=13, doc_id=144, title="제목", content="본문본문ggksjgdsljflsdjflds dsfjsdf ldsfjfdsl jfslkdsfjldfsjdsfjkldfsjlfsd ldfsj lfdslfdsj lfjdlfdsl jdfsl f jldsjfslfjdslfj slfds", image_url='', link_url='')
    bookmark_set(user_id=13, doc_id=142, title="제목", content="본문본문ggksjgdsljflsdjflds dsfjsdf ldsfjfdsl jfslkdsfjldfsjdsfjkldfsjlfsd ldfsj lfdslfdsj lfjdlfdsl jdfsl f jldsjfslfjdslfj slfds", image_url='', link_url='')
    bookmark_set(user_id=13, doc_id=132, title="제목", content="본문본문ggksjgdsljflsdjflds dsfjsdf ldsfjfdsl jfslkdsfjldfsjdsfjkldfsjlfsd ldfsj lfdslfdsj lfjdlfdsl jdfsl f jldsjfslfjdslfj slfds", image_url='', link_url='')
    
    print(bookmarks_get(user_id=223))
    print(bookmarks_get(user_id=13))

    bookmark_delete(user_id=13, doc_id=142)
    print(bookmarks_get(user_id=13))

    bookmark_delete(user_id=223, doc_id=150)
    print(bookmarks_get(user_id=223))
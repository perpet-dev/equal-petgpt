#-*- coding:utf-8 -*- 
#!/usr/bin/env python
# by Albert 
import logging
from logging.handlers import RotatingFileHandler

class LogUtil(object):
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL
    
    # Singleton 으로 구성
    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, "_instance"):         
            print("LogUtil::__new__ is called")
            cls._instance = super().__new__(cls) 
        return cls._instance 
        
    def __init__(self, logname:str='logutil', logfile_name:str='logutil.log', loglevel:int=logging.INFO, maxBytes:int=1024000, backupCount:int=5):
        cls = type(self)
        if not hasattr(cls, "_init"):           
            print("LogUtil::__init__ is called\n")
            formatter = logging.Formatter(fmt='%(levelname)s: %(name)s: %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
            self.logger = logging.getLogger(logname)
            self.logger.setLevel(logging.INFO)
            self.stream_handler = logging.StreamHandler()
            self.stream_handler.setFormatter(formatter)
            self.logger.addHandler(self.stream_handler)
            if maxBytes > 0:
                self.file_handler = RotatingFileHandler(logfile_name, mode='a', maxBytes=maxBytes, backupCount=backupCount)
            else:
                self.file_handler = logging.FileHandler(logfile_name)
            self.file_handler.setFormatter(formatter)
            self.logger.addHandler(self.file_handler)
            cls._init = True

    def setLevel(self, level:int):
        self.logger.setLevel(level)

    def debug(self, message):
        self.logger.debug(message)
    
    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)
    
    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)

if __name__ == '__main__':
    logger = LogUtil(logname='prompt_insight', logfile_name='logs/prompt_insight.log')
    logger.setLevel(logging.INFO)
    for i in  range (1, 1000000):
        logger.debug("rotaing test {}".format(i))
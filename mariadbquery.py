# from sqlalchemy import create_engine, Column, ForeignKey, Integer, String, Boolean, DateTime, text
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.orm import relationship, sessionmaker

# from config import LOG_FILE_NAME, LOGGING_LEVEL, LOG_NAME
# from log_util import LogUtil
# logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)

# Base = declarative_base()

# class User(Base):
#     __tablename__ = 'user'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     #name = Column(String(100), nullable=False, comment='이름(암호화)')
#     nickname = Column(String(255), nullable=False, comment='닉네임')
#     provider_id = "KAKAO_"# KAKAO_    3103962026
#     # other fields...
#     pets = relationship("Pet", back_populates="owner")

# class Pet(Base):
#     __tablename__ = 'pet'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     name = Column(String(6), nullable=False, comment='이름')
#     age = Column(String(10), nullable=False, comment='생일 (yyyy-mm)')
#     breeds_id = Column(Integer, ForeignKey('breeds.id'), comment='품종 고유번호')
#     user_id = Column(Integer, ForeignKey('user.id'), comment='회원 고유번호')
#     tag = Column(String(1000), comment='태그')
#     # other fields...
#     owner = relationship("User", back_populates="pets")
#     breed = relationship("Breeds", back_populates="pets")  # New relationship

# class Breeds(Base):
#     __tablename__ = 'breeds'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     name = Column(String(255), nullable=True, comment='이름')
#     type = Column(String(50), nullable=True, comment='dog:강아지, cat:고양이, etc...')
#     is_candidate = Column(Boolean, nullable=False, comment='승인되지 않은 후보 데이터 인지 여부. (true:승인되지않음. false:관리자 승인 완료)')
#     is_expired = Column(Boolean, nullable=False, comment='만료/삭제 여부. (true:더 이상 사용되지 않는 데이터, false:사용중인 데이터)')
#     is_main = Column(Boolean, nullable=False, comment='대표 데이터 여부', default=False)
#     sort_order = Column(Integer, nullable=True, comment='정렬')
#     # other fields...
#     pets = relationship("Pet", back_populates="breed")

# class Tag(Base):
#     __tablename__ = 'tag'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     insert_date = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment='등록일')
#     update_date = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment='수정일')
#     health_yn = Column(String(1), default='N', comment='건강관련 태그인지 여부')
#     medical_yn = Column(String(1), default='N', comment='문진관련 태그인지 여부')
#     name = Column(String(200), index=True)
#     used_count = Column(Integer, default=0, comment='사용횟수')

# class Banner(Base):
#     __tablename__='banner'
#     id = Column(Integer, primary_key=True, autoincrement=True)
#     insert_date = Column(DateTime, server_default=text("CURRENT_TIMESTAMP"), comment='등록일')
#     update_date = Column(DateTime, server_default=text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), comment='수정일')
#     insert_user = Column(Integer, nullable=False) 
#     link_url = Column(String(512), index=False)
#     image_url = Column(String(512), index=False)
#     update_user = Column(Integer, nullable=False)
#     use_yn = Column(Boolean, nullable=False, default=False)

# # DATABASE_URL = "mysql+pymysql://perpetdev:perpet1234!@dev.promptinsight.ai:3306/perpet"

# # engine = create_engine(DATABASE_URL, echo=True)
# # Session = sessionmaker(bind=engine)
# # session = Session()

# # for pet in session.query(Pet).join(User).join(Breeds).all():
# #     print(f"Pet Name: {pet.name}, Owner Name: {pet.owner.nickname}, Breed: {pet.breed.name}, age: {pet.age}")



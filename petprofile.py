import traceback
from mysql.connector import Error
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional
from config import LOG_FILE_NAME, LOGGING_LEVEL, LOG_NAME
from log_util import LogUtil
logger = LogUtil(logname=LOG_NAME, logfile_name=LOG_FILE_NAME, loglevel=LOGGING_LEVEL)
import logging
logger = logging.getLogger(__name__)

class Supplement(BaseModel):
    supplement_id : str
    name: str
    summary: str

class Diagnosis(BaseModel):
    diagnosis_id: str
    name: str
    health_info: str
    
from threading import Lock
class PetProfile(BaseModel):
    pet_id: int
    owner_id: int
    pet_name: str
    pet_type: str
    age: str
    gender: str
    breed: str
    weight: float
    body_weight: str
    tag_id: Optional[str] = None
    disease: Optional[str] = None  # Modify to allow None
    allergy: Optional[str] = None  # Modify to allow None
    tag: Optional[str] = None  # Allow None as a value
    diagnoses: Optional[List[Diagnosis]] = [] # Adding diagnoses to the pet profile
    supplements: Optional[List[Supplement]] = [] # Adding supplements to the pet profile
    
from db_connection import get_connection, close_connection

class PetProfileRetriever:
    _instance = None
    _lock = Lock()

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(PetProfileRetriever, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):  # Ensure __init__ runs only once
            self.connection = get_connection()
            if self.connection:
                self.cursor = self.connection.cursor()
                logger.info("Cursor created successfully.")
            else:
                self.cursor = None
                logger.error("Failed to obtain database connection from pool.")
            self.initialized = True
    
    def reconnect(self):
        """Reconnect to the database if the connection is lost."""
        self.connection = get_connection()
        if self.connection:
            self.cursor = self.connection.cursor()
            logger.info("Reconnected and cursor created successfully.")
        else:
            self.cursor = None
            logger.error("Failed to re-establish database connection.")

    def get_pet_profile(self, pet_id):
        if not self.cursor:
            self.reconnect()
            if not self.cursor:
                return None

        sql = """
            SELECT 
                p.id AS pet_id,
                p.user_id AS owner_id,
                p.name AS pet_name,
                p.type AS pet_type,
                p.age,
                p.gender,
                b.name AS breed_name,
                pp.weight,
                p.tag AS pet_tag_id,
                pp.body_form_code,
                GROUP_CONCAT(DISTINCT d.name) AS disease_names,
                GROUP_CONCAT(DISTINCT a.name) AS allergy_names,
                GROUP_CONCAT(DISTINCT t.name) AS tag_names
            FROM
                pet_profile pp
            JOIN
                pet p ON pp.pet_id = p.id
            JOIN
                breeds b ON p.breeds_id = b.id
            LEFT JOIN
                disease d ON FIND_IN_SET(d.id, pp.disease_id)
            LEFT JOIN
                allergy a ON FIND_IN_SET(a.id, pp.allergy_id)
            LEFT JOIN
                tag t ON FIND_IN_SET(t.id, p.tag)
            WHERE
                p.use_yn = 'Y' AND p.id = %s
            GROUP BY p.id;
        """

        try:
            self.cursor.execute(sql, (pet_id,))
            result = self.cursor.fetchone()
            if result:
                logger.debug("Pet profile retrieved successfully: {}".format(result))
                return self.process_pet_body_form(result)
            else:
                logger.error("No profile found for pet_id: {}".format(pet_id))
                return None
        except Exception as e:
            logger.error("Failed to execute query: {}".format(e))
            self.reconnect()  # Attempt to reconnect
            return None

    def close(self):
        if self.cursor:
            try:
                self.cursor.close()
                logger.info("Cursor closed successfully.")
            except Error as e:
                logger.error(f"Error closing cursor: {e}")

        if self.connection:
            try:
                close_connection(self.connection)
            except Error as e:
                logger.error(f"Error closing connection: {e}")

    def process_pet_body_form(self, pet_profile):
        body_form_codes = {
            '0': "저체중",
            '1': "약간 저체중",
            '2': "정상",
            '3': "준비만",
            '4': "고도비만"
        }
        body_form_code = pet_profile[9]
        body_weight = body_form_codes.get(body_form_code, "Unknown condition")

        return PetProfile(
            pet_id=pet_profile[0],
            owner_id=pet_profile[1],
            pet_name=pet_profile[2],
            pet_type=pet_profile[3],
            age=pet_profile[4],
            gender=pet_profile[5],
            breed=pet_profile[6],
            weight=pet_profile[7],
            tag_id=pet_profile[8],
            body_weight=body_weight,
            disease=pet_profile[10],
            allergy=pet_profile[11],
            tag=pet_profile[12]
        )

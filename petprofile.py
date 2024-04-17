from ipaddress import summarize_address_range
from os import name
import mysql.connector
from mysql.connector import Error
from pydantic import BaseModel, HttpUrl
from typing import Generic, TypeVar, List, Optional
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
    disease: Optional[str] = None  # Modify to allow None
    allergy: Optional[str] = None  # Modify to allow None
    tag: Optional[str] = None  # Allow None as a value
    diagnoses: Optional[List[Diagnosis]] # Adding diagnoses to the pet profile
    supplements: Optional[List[Supplement]] # Adding supplements to the pet profile
    
from config import DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE
class PetProfileRetriever():
    def __init__(self, db_host=DB_HOST, db_port=DB_PORT, db_user=DB_USER, db_password = DB_PASSWORD, db_database=DB_DATABASE):
        print('Initializing PetProfileRetriever')
        try:
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
            print('Database connection successfully established.')
        except Error as e:
            print(f"Error connecting to MariaDB Platform: {e}")
            self.connection = None
            self.cursor = None

    def get_pet_profile(self, pet_id):
        if not self.cursor:
            print("Connection was not established.")
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
                return {"error": "Pet profile not found"}
        except Exception as e:
            logger.error("Failed to execute query: {}".format(e))
            return {"error": str(e)}
        
    def close(self):
        if self.connection:
            self.cursor.close()
            self.connection.close()
            print("Database connection closed.")

    def process_pet_body_form(self, pet_profile):
        body_form_codes = {
            '0': "저체중",
            '1': "약간 저체중",
            '2': "정상",
            '3': "준비만",
            '4': "고도비만"
        }
        # Directly fetch the body form code from the tuple
        body_form_code = pet_profile[8]  
        body_weight = body_form_codes.get(body_form_code, "Unknown condition")

        # Directly return the new instance without modifying the original tuple
        return PetProfile(
            pet_id=pet_profile[0],
            owner_id=pet_profile[1],
            pet_name=pet_profile[2],
            pet_type=pet_profile[3],
            age=pet_profile[4],
            gender=pet_profile[5],
            breed=pet_profile[6],
            weight=pet_profile[7],
            body_weight=body_weight,
            disease=pet_profile[9],
            allergy=pet_profile[10],
            tag=pet_profile[11]
        )

"""
Configuration et connexion à MongoDB
Utilise Motor pour les opérations asynchrones
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "emiliehhdoan_db_user")

# Client MongoDB 
client = None
database = None
sync_client = None  

async def connect_to_mongo():
    global client, database
    client = AsyncIOMotorClient(MONGODB_URL)
    database = client[DATABASE_NAME]
    print(f"Connecté à MongoDB: {DATABASE_NAME}")

async def close_mongo_connection():
    if client:
        client.close()
        print("Connexion MongoDB fermée")

def get_database():
    return database

def get_collection(collection_name: str):
    # if database is not None:
        # sync_client = MongoClient(MONGODB_URL)
        # sync_db = sync_client[DATABASE_NAME]
        # return sync_db[collection_name]
    return database[collection_name]
    # return None
from enum import Enum
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class Status(Enum):
    IDLE = "idle"
    PENDING = "pending"
    RECEIVED = "received"
    FINISHED = "finished"

class Plant(Enum):
    AVOCADO = "avocado"
    KAREL = "karel"

class Collection(Enum):
    REQUESTS = "requests"

class Requests(Enum):
    WATER = "water"
    TAKE_PHOTO = "take_photo"
    

def read_from_db_status(db: firestore.Client, collection: Collection, status: Status):
    return db.collection(collection.value).where(filter=FieldFilter('status', '==', status.value)).get()
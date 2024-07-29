from enum import Enum
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter


class Status(str, Enum):
    idle = "idle"
    pending = "pending"
    received = "received"
    finished = "finished"
    failed = "failed"

class Plant(str, Enum):
    avocado = "avocado"
    karel = "karel"

class Collection(str, Enum):
    requests = "requests"

class Requests(str, Enum):
    water = "water"
    take_photo = "take_photo"
    push_to_git = "push_to_git"
    record_video = "record_video"

plant_to_GPIO_map = {
    Plant.avocado : 26, 
    Plant.karel : 21
    }

def read_from_db_status(db: firestore.Client, collection: Collection, status: Status):
    return db.collection(collection.value).where(filter=FieldFilter('status', '==', status.value)).get()
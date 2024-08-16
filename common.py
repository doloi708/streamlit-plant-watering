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
    bylinky = "bylinky"

class Collection(str, Enum):
    requests = "requests"

class Requests(str, Enum):
    water = "water"
    take_photo = "take_photo"
    push_to_git = "push_to_git"
    record_video = "record_video"

plant_to_GPIO_map = {
    Plant.avocado : 5, 
    Plant.karel : 27
    }

device_id_to_Plants = {
    0 : [Plant.avocado, Plant.karel],
    1 : [Plant.bylinky]
}


VLOGS_RELATIVE_DIR = "../plant-watering-vlogs/"

def read_from_db_status(db: firestore.Client, collection: Collection, status: Status):
    return db.collection(collection.value).where(filter=FieldFilter('status', '==', status.value)).get()


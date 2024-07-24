import firebase_admin
import json
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import time

from common import Status, Plant

BACKEND_ID = 1


cred = credentials.Certificate('firestore-key.json')
app = firebase_admin.initialize_app(cred, name=f"backend_ID{BACKEND_ID}")
db = firestore.client(app)



def listen_for_requests(db: firestore.Client):
    # return read_from_db_status
    return db.collection("requests").where(filter=FieldFilter('status', '==', Status.PENDING.value)).get()


def process_request(db, request: firestore.DocumentSnapshot):
    db.collection("requests").document(request.id).set({"status" : Status.RECEIVED.value}, merge=True)

    time.sleep(2)

    db.collection("requests").document(request.id).set({"status" : Status.FINISHED.value}, merge=True)


###################################################
#################### MAIN LOOP ####################
###################################################

# while(True):

pending_requests = listen_for_requests(db)

if pending_requests:
    for request in pending_requests:
        process_request(db, request)

# time.sleep(10)
    



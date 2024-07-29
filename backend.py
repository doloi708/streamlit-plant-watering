import sys
import firebase_admin
import json
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import time
import threading

from common import Requests, Status, Plant, plant_to_GPIO_map

try:
    import RPi.GPIO as GPIO
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FfmpegOutput
except ModuleNotFoundError:
    print("=== [Debug] Module(s) not found, probably not running this script on RPi")


def water_plant(plant: Plant, duration: int, db: firestore.Client):
    """[Thread] Watering a plant with duration. Upon ending, writes into the database. 
    """
    # Adding a short sleep in case of recording a video  
    time.sleep(2)

    GPIO_pin = plant_to_GPIO_map[plant.value]
    print(f"=== [Watering] {plant.value} on GPIO: {GPIO_pin} for {duration} seconds. ===")
    try:
        GPIO.output(GPIO_pin, True)
        time.sleep(duration)
        print("=== [Watering] succesfully ended ===")
        GPIO.output(GPIO_pin, False)
    except NameError:
        time.sleep(duration)
        print("=== [Watering][Debug] GPIO not set. Probably not running this script on RPi ===")
    print(f"=== [Watering] {plant.value} ended. ===")
    db.collection("requests").document(request.id).set({"status" : Status.finished.value}, merge=True)


def record_video(plant: Plant, duration: int, db: firestore.Client):
    pass

def listen_for_requests(db: firestore.Client):
    """Listen for PENDING requests
    """
    return db.collection("requests").where(filter=FieldFilter('status', '==', Status.pending.value)).get()


def process_request(db, request: firestore.DocumentSnapshot):
    """Process a single request in a thread
    """
    db.collection("requests").document(request.id).set({"status" : Status.received.value}, merge=True)
    request_data = request.to_dict()

    ### Watering
    if request_data["request_type"] == Requests.water:
        # Parameters
        plant = Plant[request_data["plant_name"]]
        watering_duration = request_data["duration"]

        # Start the thread:
        thread_pumping = threading.Thread(target=water_plant, args=(plant, watering_duration, db))
        thread_pumping.start()

    ### Record a video
    elif request_data["request_type"] == Requests.record_video:
        plant = Plant[request_data["plant_name"]]
        video_duration = request_data["duration"]        
        # Start the thread:
        thread_pumping = threading.Thread(target=water_plant, args=(plant, video_duration, db))
        time.sleep(2)
        thread_pumping.start()

    elif request_data["request_type"] == Requests.take_photo:
        pass
        #TODO
    elif request_data["request_type"] == Requests.push_to_git:
        pass
    else:
        pass


###################################################
#################### MAIN LOOP ####################
###################################################

if __name__ == "__main__":
    BACKEND_ID = 1

    # setup_GPIO()


    cred = credentials.Certificate('firestore-key.json')
    app = firebase_admin.initialize_app(cred, name=f"backend_ID{BACKEND_ID}")
    db = firestore.client(app)

    try:
        while(True):
            print("============================")
            print("=== Reading for requests ===")
            print("============================")
            pending_requests = listen_for_requests(db)

            if pending_requests:
                for request in pending_requests:
                    process_request(db, request)

            time.sleep(10)
    except KeyboardInterrupt:
        print("=== Interupted, the script is terminating ===")
        # TODO: switch to a different regime instead
        sys.exit()



import os
import sys
import firebase_admin
import json
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import time
import threading
import datetime
from git import Repo

PATH_OF_GIT_REPO = r'/home/loido/git_repositories/plant-watering-vlogs/.git'  # make sure .git folder is properly configured
COMMIT_MESSAGE = 'Adding vlogs'


from common import VLOGS_RELATIVE_DIR, Requests, Status, Plant, plant_to_GPIO_map, device_id_to_Plants

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
        GPIO.output(GPIO_pin, False)
    except NameError:
        time.sleep(duration)
        print("=== [Watering][Debug] GPIO not set. Probably not running this script on RPi ===")
    print(f"=== [Watering] {plant.value} ended. ===")
    db.collection("requests").document(request.id).set({"status" : Status.finished.value}, merge=True)


# def gitPush():
#     print("=== Pushing video to git ===")
#     os.chdir("../plant-watering-vlogs")
#     os.system("git pull")
#     os.system("git add .")
#     os.system("git commit -m'Adding data'")
#     os.system("git push")
#     os.chdir("../streamlit-plant-watering")

def git_push():
    try:
        repo = Repo(PATH_OF_GIT_REPO)
        repo.git.add(".")
        repo.index.commit(COMMIT_MESSAGE)
        origin = repo.remote(name='origin')
        origin.push()
    except:
        print('Some error occured while pushing the code') 


def record_video(plant: Plant, duration: int, timestamp: str, db: firestore.Client):
    """[Thread] Record a video with diration. Upon ending, writes into the database
    """
    filename = f"{VLOGS_RELATIVE_DIR}Plant_{plant.name}_{timestamp}.h264"
    try:
        picam2 = Picamera2()
        video_config = picam2.create_video_configuration()
        picam2.configure(video_config)
        print(f"=== [Recording] {plant.value}: video for {duration} seconds. ===")
        picam2.start_recording(H264Encoder(10000000), filename)
        time.sleep(duration)
        picam2.stop_recording()
        print("=== End recording video ===")
        time.sleep(1)
        git_push()
    except NameError:
        print(f"=== [Recording][Debug] {plant.value}: video for {duration} seconds. ===")
    db.collection("requests").document(request.id).set({"status" : Status.finished.value}, merge=True)


def listen_for_requests(db: firestore.Client, active_plants: list[Plant]):
    """Listen for PENDING requests
    """
    return (
        db.collection("requests")
        .where(filter=FieldFilter('status', '==', Status.pending.value))
        .where(filter=FieldFilter('plant_name', 'in', active_plants))
        .get()
        )


def process_request(db, request: firestore.DocumentSnapshot, BACKEND_ID=0):
    """Process a single request in a thread
    """
    
    request_data = request.to_dict()

    ### Watering
    if request_data["request_type"] == Requests.water and BACKEND_ID == 0:
        db.collection("requests").document(request.id).set({"status" : Status.received.value}, merge=True)
        # Parameters
        plant = Plant[request_data["plant_name"]]
        watering_duration = request_data["duration"]

        # Start the thread:
        water_plant(plant, watering_duration, db)

    ### Record a video
    if request_data["request_type"] == Requests.record_video and BACKEND_ID == 1:
        db.collection("requests").document(request.id).set({"status" : Status.received.value}, merge=True)
        plant = Plant[request_data["plant_name"]]
        video_duration = request_data["duration"]        
        timestamp = request_data["timestamp"]

        # Start the thread:
        # time.sleep(2)
        record_video(plant, video_duration, timestamp, db)
        # thread_video = threading.Thread(target=record_video, args=())
        
        # thread_video.start()

def setup_GPIO(GPIO_pin: int, plant: Plant):
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_pin, GPIO.OUT)
        GPIO.setwarnings(False)
        GPIO.output(GPIO_pin, False)
        print(f"=== [GPIO] Setting up GPIO {GPIO_pin} that controls the watering of a plant {plant.value}. ===")
    except NameError:
        print(f"=== [GPIO][Debug] Setting up GPIO {GPIO_pin} that controls the watering of a plant {plant.value}.")


###################################################
#################### MAIN LOOP ####################
###################################################

if __name__ == "__main__":
    try:
        BACKEND_ID = int(sys.argv[1])
    except IndexError:
        BACKEND_ID = 0
        print(f"=== [Debug] The ID of the device is {BACKEND_ID}. ===")
    
    active_plants = device_id_to_Plants[BACKEND_ID]
    active_GPIOs = [plant_to_GPIO_map[plant] for plant in active_plants]
    if BACKEND_ID == 0:
        for gpio, plant in zip(active_GPIOs, active_plants):
            setup_GPIO(gpio, plant)


    cred = credentials.Certificate('firestore-key.json')
    app = firebase_admin.initialize_app(cred, name=f"backend_ID{BACKEND_ID}")
    db = firestore.client(app)


    try:
        print("========================================")
        print("=== Synchronizing with other devices ===")
        timeout = 0
        while (curr_time := datetime.datetime.now().time().second) != 0 and timeout < 30:
            time.sleep(0.1)
            timeout += 0.1
        print(f"===Device synchronized at time {curr_time}===")

        while(True):
            print("============================")
            print("=== Reading for requests ===")
            print("============================")
            pending_requests = listen_for_requests(db, active_plants)

            if pending_requests:
                for request in pending_requests:
                    process_request(db, request, BACKEND_ID)

            time.sleep(10)
    except KeyboardInterrupt:
        print("=== Interupted, the script is terminating ===")
        # TODO: switch to a different regime instead
        GPIO.cleanup()
        sys.exit()



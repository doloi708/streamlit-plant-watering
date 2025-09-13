import sys
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
import time
import datetime
import logging
from logging.handlers import RotatingFileHandler

logger = logging.getLogger("mylogger")
logger.setLevel(logging.INFO)
file_name = f"output_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
handler = RotatingFileHandler(file_name, maxBytes=5 * 1024 * 1024, backupCount=3)
formatter = logging.Formatter('%(asctime)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

PATH_OF_GIT_REPO = r'/home/loido/git_repositories/plant-watering-vlogs/.git'  # make sure .git folder is properly configured
COMMIT_MESSAGE = 'Adding vlogs'
REINIT_INTERVAL_SECONDS = 3600  # 1 hour

from common import VLOGS_RELATIVE_DIR, Requests, Status, Plant, plant_to_GPIO_map, device_id_to_Plants

try:
    import RPi.GPIO as GPIO
except ModuleNotFoundError:
    logger.info("=== GPIO Module not found, probably not running this script on RPi")

try:
    from picamera2 import Picamera2
    from picamera2.encoders import H264Encoder
    from picamera2.outputs import FfmpegOutput
except ModuleNotFoundError:
    logger.info("=== Camera module not found, probably not running this script on RPi")

def water_plant(plant: Plant, duration: int, request, db: firestore.Client):
    """[Thread] Watering a plant with duration. Upon ending, writes into the database. 
    """
    # Adding a short sleep in case of recording a video  
    time.sleep(2)

    GPIO_pin = plant_to_GPIO_map[plant.value]
    logger.info(f"=== [Watering] {plant.value} on GPIO: {GPIO_pin} for {duration} seconds. ===")
    try:
        GPIO.output(GPIO_pin, True)
        time.sleep(duration)
        GPIO.output(GPIO_pin, False)
    except NameError:
        time.sleep(duration)
        logger.info("=== [Watering][Debug] GPIO not set. Probably not running this script on RPi ===")
    logger.info(f"=== [Watering] {plant.value} ended. ===")
    db.collection("requests").document(request.id).set({"status" : Status.finished.value}, merge=True)


def record_video(plant: Plant, duration: int, timestamp: str, request, db: firestore.Client):
    """[Thread] Record a video with diration. Upon ending, writes into the database
    """
    filename = f"{VLOGS_RELATIVE_DIR}Plant_{plant.name}_{timestamp}.h264"
    try:
        picam2 = Picamera2()
        video_config = picam2.create_video_configuration()
        picam2.configure(video_config)
        logger.info(f"=== [Recording] {plant.value}: video for {duration} seconds. ===")
        picam2.start_recording(H264Encoder(10000000), filename)
        time.sleep(duration)
        picam2.stop_recording()
        picam2.close()
        logger.info("=== End recording video ===")
        db.collection("requests").document(request.id).set({"status" : Status.finished.value}, merge=True)
    except NameError:
        logger.error(f"=== [Recording][Debug] {plant.value}: video for {duration} seconds. ===")
    

def listen_for_requests(db: firestore.Client, active_plants: list[Plant]):
    """Listen for PENDING requests
    """

    try:
        requests = db.collection("requests").where(filter=FieldFilter('status', '==', Status.pending.value)).where(filter=FieldFilter('plant_name', 'in', active_plants)).get()
    except BaseException as e:
        requests = []
        logger.error(f"An error has occured. Returing empty array. Traceback: {e}")
    return requests


def process_request(db, request: firestore.DocumentSnapshot, BACKEND_ID):
    """Process a single request in a thread
    """
    
    request_data = request.to_dict()

    ### Watering
    if (request_data["request_type"] == Requests.water) and BACKEND_ID == 0:
        db.collection("requests").document(request.id).set({"status" : Status.received.value}, merge=True)
        # Parameters
        plant = Plant[request_data["plant_name"]]
        watering_duration = request_data["duration"]

        # Start the thread:
        water_plant(plant, watering_duration, request, db)

    ### Record a video
    elif (request_data["request_type"] == Requests.record_video) and BACKEND_ID == 1:
        db.collection("requests").document(request.id).set({"status" : Status.received.value}, merge=True)
        plant = Plant[request_data["plant_name"]]
        video_duration = request_data["duration"]        
        timestamp = request_data["timestamp"]

        # Start the thread:
        record_video(plant, video_duration, timestamp, request, db)
        

def setup_GPIO(GPIO_pin: int, plant: Plant):
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(GPIO_pin, GPIO.OUT)
        GPIO.setwarnings(False)
        GPIO.output(GPIO_pin, False)
        logger.info(f"=== [GPIO] Setting up GPIO {GPIO_pin} that controls the watering of a plant {plant.value}. ===")
    except NameError:
        logger.info(f"=== [GPIO][Debug] Setting up GPIO {GPIO_pin} that controls the watering of a plant {plant.value}.")

# Initialize Firebase Admin SDK (with a function for re-initialization)
def initialize_firebase_app(backend_id: int = 0):
    try:
        cred = credentials.Certificate('firestore-key.json')
        app_name = f"backend_ID{backend_id}_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        app = firebase_admin.initialize_app(cred, name=app_name)
        db = firestore.client(app)
        logger.info("=== Firebase App Initialized ===")
        return app, db
    except Exception as e:
        logger.error(f"=== Error initializing Firebase App: {e} ===")
        return None, None


###################################################
#################### MAIN LOOP ####################
###################################################

def main():
    try:
        BACKEND_ID = int(sys.argv[1])
    except IndexError:
        BACKEND_ID = 0
        logger.info(f"=== [Debug] The ID of the device is {BACKEND_ID}. ===")
    
    # ====== INIT ======
    last_reinit_time = time.time()  # Initialize the last re-initialization time
    active_plants = device_id_to_Plants[BACKEND_ID]
    active_GPIOs = [plant_to_GPIO_map[plant] for plant in active_plants]
    if BACKEND_ID == 0:
        for gpio, plant in zip(active_GPIOs, active_plants):
            setup_GPIO(gpio, plant)

    app, db = initialize_firebase_app(BACKEND_ID)  # Re-initialize
    try:
        while(True):
            try:
                # Check if it's time to re-initialize the Firebase app
                if time.time() - last_reinit_time >= REINIT_INTERVAL_SECONDS:
                    logger.info("=== Re-initializing Firebase App ===")
                    last_reinit_time = time.time()  # Update the last re-initialization time
                    if app:
                        try:
                            firebase_admin.delete_app(app)  # Delete the existing app
                            logger.info("=== Firebase App deleted successfully ===")
                        except Exception as e:
                            logger.error(f"=== Error deleting existing Firebase App: {e} ===")

                    app, db = initialize_firebase_app(BACKEND_ID)  # Re-initialize
                if db is None:
                    logger.error("=== Failed to re-initialize Firebase App. Retrying in 10 seconds. ===")
                    time.sleep(10)
                    continue  # Skip the rest of the loop and retry

                logger.info("=== Reading for requests ===")
                pending_requests = listen_for_requests(db, active_plants)

                if pending_requests:
                    for request in pending_requests:
                        process_request(db, request, BACKEND_ID)
            except BaseException as e:
                logger.error("=== Error while listening for requests or initializing the connection. ===")
                logger.error(f"=== Error: {e} ===")
                logger.info("=== Retrying in 10 seconds. ===")
                time.sleep(30)
            time.sleep(10)  # Wait for 1 second before checking again)
    except KeyboardInterrupt:
        logger.info("=== Interupted, the script is terminating ===")
        # TODO: switch to a different regime instead
        GPIO.cleanup()
        sys.exit()

main()


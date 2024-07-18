import time
from enum import Enum
import streamlit as st

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


ASK_PERIOD = 5
TIMEOUT_TIME = 10

class Plant(Enum):
    AVOCADO = 1
    KAREL = 2

## Init connection to database
if "db" not in st.session_state:
    if not firebase_admin._apps:
        cred = credentials.Certificate("./firestore-key.json")
        firebase_admin.initialize_app(cred)
    st.session_state.db = firestore.client()


def is_request_watering_plant_sent(db, plant: Plant):
    return db.collection("task").document(f"water_{plant.name}").get().to_dict()["is_on"]


def set_watering_plant(db, plant: Plant, val: bool):
    db.collection("task").document(f"water_{plant.name}").set(
        {
            "is_on" : val
        }
    )


def water_plant(db, plant: Plant):
    if not is_request_watering_plant_sent(db, plant):
        st.toast("Sending request to water Avocado!")
        set_watering_plant(db, Plant.AVOCADO, True)
    else:
        st.toast('Request to water the avocado was already sent.')
    

def is_RPi_watering_responded(db, plant: Plant):
    """Returns True if RPi received request to water Avocado
    """
    return db.collection("RPi_response").document(f"water_{plant.name}").get().to_dict()["acknowledged"]

def reset_handshake_watering(db, plant: Plant):
    """Reset the handshake
    """
    db.collection("RPi_response").document(f"water_{plant.name}").set(
        {
            "acknowledged" : False
        }
    )

def toggle_LED(db):
    current_status = db.collection("task").document("turn_on_LED").get().to_dict()["is_on"]
    db.collection("task").document("turn_on_LED").set(
    {
        "is_on" : not current_status
    }
)


st.set_page_config(
    page_title="Watering our plants",
    page_icon="🥬",
    layout="wide",
)


st.header('Plant watering')

### Avocado
if st.button('Water Avocado!'):
    water_plant(st.session_state.db, Plant.AVOCADO)
    with st.spinner('Waiting for response from RPI.'):
        # Avocado is watering. Please wait!
        timeout = 0
        while not (RPi_responded := is_RPi_watering_responded(st.session_state.db, Plant.AVOCADO)) and timeout < TIMEOUT_TIME:
            time.sleep(ASK_PERIOD)
            timeout += ASK_PERIOD
        if RPi_responded:
            st.success("RPi recieved the request to water Avocado and proceeds to watering!", icon="✅")
            reset_handshake_watering(st.session_state.db, Plant.AVOCADO)
        else:
            st.warning("RPi has not recieved the request to water Avocado, try again!", icon="⚠️")
        # Resetting watering Avocado
        set_watering_plant(st.session_state.db, Plant.AVOCADO, False)


if st.button('Toggle LED'):
    toggle_LED(st.session_state.db)


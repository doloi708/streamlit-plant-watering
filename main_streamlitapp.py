import time
from enum import Enum
import streamlit as st
import json
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


# from google.cloud import firestore

TIMEOUT_TIME = 10 # In seconds

class Status(Enum):
    IDLE = "idle"
    PENDING = "pending"
    RECEIVED = "received"

class Plant(Enum):
    AVOCADO = 1
    KAREL = 2

## Init connection to database
if "db" not in st.session_state:
    if not firebase_admin._apps:
        key_dict = json.loads(st.secrets["textkey"])
        cred = credentials.Certificate(key_dict)
        firebase_admin.initialize_app(cred)
    st.session_state.db = firestore.client()


def is_request_watering_plant_sent(db, plant: Plant):
    return db.collection("requests").document(f"water_{plant.name}").get().to_dict()["status"] != Status.IDLE.value


def set_watering_plant(db, plant: Plant, status: Status):
    db.collection("requests").document(f"water_{plant.name}").set(
        {
            "status" : status.value 
        }
    )


def water_plant(db, plant: Plant):
    if not is_request_watering_plant_sent(db, plant):
        st.toast("Sending request to water Avocado!")
        set_watering_plant(db, Plant.AVOCADO, Status.PENDING)
    else:
        st.toast('Request to water the avocado was already sent.')
    

def is_RPi_watering_responded(db, plant: Plant):
    """Returns True if RPi received request to water Avocado
    """
    return db.collection("requests").document(f"water_{plant.name}").get().to_dict()["status"] == Status.RECEIVED.value


def toggle_LED(db):
    current_status = db.collection("requests").document("turn_on_LED").get().to_dict()["is_on"]
    db.collection("requests").document("turn_on_LED").set(
    {
        "is_on" : not current_status
    }
)


st.set_page_config(
    page_title="Watering our plants",
    page_icon="🥬",
    layout="wide",
)

##########################################xx
##########################################xx

with open('./config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

    config['credentials']["usernames"]["user"]["password"] = st.secrets["passwords"]["User"]

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days'],
)


# Creating a login widget
authenticator.login()
if st.session_state["authentication_status"]:
    authenticator.logout()
elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

if not st.session_state["authentication_status"]:
    st.stop()  # Do not continue if check_password is not True.


st.header('Plant watering', divider='rainbow')
query_period = st.number_input("Query period (s)", value = 5)
timeout = st.number_input("Timeout (s)", value = 10)
col1, col2 = st.columns([0.2, 0.2])
### Avocado
with col1:
    with st.form("avocado_form"):
        st.subheader('Avocado')
        number = st.number_input("Watering Duration (s)", value = 10)
        # Every form must have a submit button.
        submitted = st.form_submit_button("Send!")
        if submitted:
            water_plant(st.session_state.db, Plant.AVOCADO)
            with st.spinner('Waiting for response from RPI.'):
                # Avocado is watering. Please wait!
                time_counter = 0
                while not (RPi_responded := is_RPi_watering_responded(st.session_state.db, Plant.AVOCADO)) and time_counter < timeout:
                    time.sleep(query_period)
                    time_counter += query_period
                if RPi_responded:
                    st.success("RPi recieved the request to water Avocado and proceeds to watering!", icon="✅")
                else:
                    st.warning("RPi has not recieved the request to water Avocado, try again!", icon="⚠️")
                # Resetting watering Avocado
                set_watering_plant(st.session_state.db, Plant.AVOCADO, Status.IDLE)
        

if st.button('Toggle LED'):
    toggle_LED(st.session_state.db)




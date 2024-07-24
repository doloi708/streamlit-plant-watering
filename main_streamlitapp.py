import time
import streamlit as st
import json
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import datetime
import pandas as pd

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore

from common import Requests, Status, Plant, Collection, read_from_db_status
# from google.cloud import firestore

TIMEOUT_TIME = 30 # In seconds


## Init connection to database
if "db" not in st.session_state:
    key_dict = json.loads(st.secrets["textkey"])
    cred = credentials.Certificate(key_dict)
    app = firebase_admin.initialize_app(cred, name=f"front-end_{datetime.datetime.now()}")
    st.session_state.db = firestore.client(app)


def is_request_watering_plant_sent(db, plant: Plant):
    return db.collection("requests").document(f"water_{plant.name}").get().to_dict()["status"] != Status.IDLE.value


def set_watering_plant(db, plant: Plant, status: Status, duration: int = 10):
    document_data = {
        'request_type' : Requests.WATER.value,
        'plant_name': plant.value,
        'status': status.value,
        'duration': duration,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d-%H:%M:%S')
    }
    # Create a new document in the collection
    doc_ref = db.collection(Collection.REQUESTS.value).document()
    doc_ref.set(document_data)
    st.success(f"Request with a id {doc_ref.id} succesfully sent!", icon="✅")



def display_requests(requests: list):
    if requests:
        requests_dict = {}
        for idx, request in enumerate(requests):
            requests_dict[idx] = request.to_dict()
        st.dataframe(pd.DataFrame.from_dict(requests_dict, orient='index'))
    else:
        st.info("No requests", icon='🚩')

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

st.subheader("Requests viewer")
with st.form("read_requests"):
    col1, col2, col3 = st.columns([0.3, 0.3, 0.3])
    ####
    if st.form_submit_button("Update Requests"):
        with col1:
            st.markdown('**Pending requests**')
            pending_requests = read_from_db_status(st.session_state.db, Collection.REQUESTS, Status.PENDING)
            display_requests(pending_requests)
        with col2:
            st.markdown('**Received requests**')
            received_requests = read_from_db_status(st.session_state.db, Collection.REQUESTS, Status.RECEIVED)
            display_requests(received_requests)
        with col3:
            st.markdown('**Finished requests**')
            finished_requests = read_from_db_status(st.session_state.db, Collection.REQUESTS, Status.FINISHED)
            display_requests(finished_requests)

col1, col2, col3 = st.columns([0.3, 0.3 ,0.3])
### Avocado
with col1:
    st.subheader('Avocado')

    with st.form("avocado_watering_form"):
        st.subheader('Watering')
        duration = st.number_input("Watering Duration (s)", value = 10)
        if st.form_submit_button("Send!"):
            set_watering_plant(st.session_state.db, Plant.AVOCADO, Status.PENDING, duration)


if st.button("Delete finished requests"):
    collection_ref = st.session_state.db.collection(Collection.REQUESTS.value)

    # Query for documents where "status" is "finished"
    docs = collection_ref.where('status', '==', Status.FINISHED.value).stream()
    num_of_docs = len(list(docs))
    # Delete each matching document
    for doc in docs:
        doc.reference.delete()
    
    st.info(f"{num_of_docs} finished request(s) succesfully deleted.", icon='✅')




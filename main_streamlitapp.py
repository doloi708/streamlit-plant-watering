import time
import streamlit as st
import json
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
import datetime
import pandas as pd
from google.cloud.firestore_v1.base_query import FieldFilter
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
    return db.collection("requests").document(f"water_{plant.name}").get().to_dict()["status"] != Status.idle.value


def set_request_plant(db, request: Requests, plant: Plant, status: Status, duration: int = 10):
    document_data = {
        'request_type' : request.value,
        'plant_name': plant.value,
        'status': status.value,
        'duration': duration,
        'timestamp': datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    }
    # Create a new document in the collection
    doc_ref = db.collection(Collection.requests.value).document()
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
    return db.collection("requests").document(f"water_{plant.name}").get().to_dict()["status"] == Status.received.value


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
            pending_requests = read_from_db_status(st.session_state.db, Collection.requests, Status.pending)
            display_requests(pending_requests)
        with col2:
            st.markdown('**Received requests**')
            received_requests = read_from_db_status(st.session_state.db, Collection.requests, Status.received)
            display_requests(received_requests)
        with col3:
            st.markdown('**Finished requests**')
            finished_requests = read_from_db_status(st.session_state.db, Collection.requests, Status.finished)
            display_requests(finished_requests)

col1, col2, col3 = st.columns([0.3, 0.3 ,0.3])
### Avocado
with col1:
    st.subheader('Avocado')

    with st.form("avocado_watering_form"):
        st.subheader('Watering')
        watering_duration = st.number_input("Watering Duration (s)", value = 10)

        _col1, _col2 = st.columns([0.5, 0.5])
        with _col1:
            checkbox_record_video = st.checkbox("Recond a Video")
        with _col2:
            video_duration = st.number_input("Record Duration (s)", value = watering_duration + 5)
            
        if st.form_submit_button("Send!"):
            set_request_plant(st.session_state.db, Requests.water, Plant.avocado, Status.pending, watering_duration)
            if checkbox_record_video:
                set_request_plant(st.session_state.db, Requests.record_video, Plant.avocado, Status.pending, video_duration)

### Karel
with col2:
    st.subheader('Karel')

    with st.form("karel_watering_form"):
        st.subheader('Watering')
        watering_duration = st.number_input("Watering Duration (s)", value = 10)

        _col1, _col2 = st.columns([0.5, 0.5])
        with _col1:
            checkbox_record_video = st.checkbox("Recond a Video")
        with _col2:
            video_duration = st.number_input("Record Duration (s)", value = watering_duration + 5)
            
        if st.form_submit_button("Send!"):
            set_request_plant(st.session_state.db, Requests.water, Plant.karel, Status.pending, watering_duration)
            if checkbox_record_video:
                set_request_plant(st.session_state.db, Requests.record_video, Plant.karel, Status.pending, video_duration)


if st.button("Delete finished requests"):
    collection_ref = st.session_state.db.collection(Collection.requests.value)

    # Query for documents where "status" is "finished"
    docs = collection_ref.where(filter=FieldFilter('status', '==', Status.finished.value)).get()
    num_of_docs = len(docs)

    # Delete each matching document
    for doc in docs:
        doc.reference.delete()
    
    st.info(f"{num_of_docs} finished request(s) succesfully deleted.", icon='✅')




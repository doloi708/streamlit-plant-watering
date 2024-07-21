import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


# Initialize Firebase Admin SDK
cred = credentials.Certificate('firestore-key.json')  # Replace with your service account key file path
firebase_admin.initialize_app(cred)

db = firestore.client()

# Define the collection name
collection_name = 'my_new_collection'

# Define the document structure
document_data = {
    'field1': 'value1',
    'field2': 123,
    'field3': True,
    'field4': ['item1', 'item2'],
    'field5': {
        'nested_field1': 'nested_value1',
        'nested_field2': 456
    }
}

# Create a new document in the collection
doc_ref = db.collection(collection_name).document()
doc_ref.set(document_data)

print(f'Document added to collection {collection_name}: {doc_ref.id}')
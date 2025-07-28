import hashlib 
import json
from time import time

def hash_data(data):
    """Create a SHA256 hash of the given data."""
    data_string = json.dumps(data, sort_keys=True).encode()
    return hashlib.sha256(data_string).hexdigest()

def current_time():
    return int(time())

def generate_txid(transaction):
    """Generate a unique transaction ID from the transaction data."""
    return hash_data(transaction)

import pg8000.native

DB_CONFIG = {
    "host": "localhost",
    "port": 26257,
    "database": "globalshop",
    "user": "root",
    "password": None,
}

def get_connection():
    return pg8000.native.Connection(**DB_CONFIG)
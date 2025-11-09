import os
import mysql.connector
from dotenv import load_dotenv
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

def get_db_connection():
    host = os.getenv('DB_HOST','localhost')
    user = os.getenv('DB_USER','root')
    password = os.getenv('DB_PASSWORD','')
    database = os.getenv('DB_NAME','Car_Rental')
    port = int(os.getenv('DB_PORT','3306'))
    conn = mysql.connector.connect(
        host=host, user=user, password=password, database=database, port=port
    )
    return conn

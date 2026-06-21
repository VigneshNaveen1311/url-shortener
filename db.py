import psycopg

def get_connection():
    return psycopg.connect(
        host="postgres",
        port=5432,
        dbname="url_shortener",
        user="postgres",
        password="123"
    )
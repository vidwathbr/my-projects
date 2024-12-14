import mysql.connector

def get_db_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='',
        database='crypto_currency'
    )

def create_user(name, email, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO User (name, email, password) VALUES (%s, %s, %s)", (name, email, password))
    conn.commit()
    cursor.close()
    conn.close()
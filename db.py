import mysql.connector
from config import setting

def conn():
    return mysql.connector.connect(
        host=setting("DB_HOST", "127.0.0.1"),
        port=int(setting("DB_PORT", "3306")),
        database=setting("DB_NAME", "baliraja"),
        user=setting("DB_USER", "baliraja_user"),
        password=setting("DB_PASSWORD", "")
    )

def query(sql, params=()):
    c = conn()
    cur = c.cursor(dictionary=True)
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    c.close()
    return rows

def execute(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    c.commit()
    last_id = cur.lastrowid
    cur.close()
    c.close()
    return last_id

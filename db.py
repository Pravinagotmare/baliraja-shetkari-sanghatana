import hashlib

import streamlit as st
from mysql.connector.pooling import MySQLConnectionPool

from config import setting


@st.cache_resource
def _connection_pool(host, port, database, user, password):
    pool_key = hashlib.sha1(
        f"{host}|{port}|{database}|{user}|{password}".encode("utf-8")
    ).hexdigest()[:10]
    return MySQLConnectionPool(
        pool_name=f"baliraja_{pool_key}",
        pool_size=4,
        pool_reset_session=True,
        host=host,
        port=port,
        database=database,
        user=user,
        password=password,
        connection_timeout=5,
        autocommit=False,
    )


def conn():
    return _connection_pool(
        setting("DB_HOST", "127.0.0.1"),
        int(setting("DB_PORT", "3306")),
        setting("DB_NAME", "baliraja"),
        setting("DB_USER", "baliraja_user"),
        setting("DB_PASSWORD", ""),
    ).get_connection()


def _query_uncached(sql, params=()):
    connection = conn()
    try:
        cursor = connection.cursor(dictionary=True)
        try:
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
    finally:
        connection.close()


@st.cache_data(ttl=15, show_spinner=False)
def _cached_query(sql, params=()):
    return _query_uncached(sql, params)


def query(sql, params=()):
    # Never put password hashes or other user-table records in the shared cache.
    if "users" in sql.lower():
        return _query_uncached(sql, params)
    return _cached_query(sql, params)


def execute(sql, params=()):
    connection = conn()
    try:
        cursor = connection.cursor()
        try:
            cursor.execute(sql, params)
            connection.commit()
            last_id = cursor.lastrowid
        except Exception:
            connection.rollback()
            raise
        finally:
            cursor.close()
    finally:
        connection.close()

    # Reruns after a write must immediately see the updated database state.
    _cached_query.clear()
    return last_id

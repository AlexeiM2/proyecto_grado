# database.py
import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "homicidios.db"
CSV_PATH = "homicidios_completo_limpio.csv"

def crear_db_si_no_existe():
    """
    Intenta crear la base SQLite si existe el CSV.
    NO detiene la app si falla.
    """
    if os.path.exists(DB_PATH):
        return True

    if not os.path.exists(CSV_PATH):
        return False

    try:
        df = pd.read_csv(CSV_PATH)
        df = df.loc[:, ~df.columns.str.contains("^unnamed", case=False)]
        conn = sqlite3.connect(DB_PATH)
        df.to_sql("homicidios", conn, if_exists="replace", index=False)
        conn.close()
        return True
    except Exception as e:
        st.warning(f"⚠️ No se pudo crear SQLite: {e}")
        return False


@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)

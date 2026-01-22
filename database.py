# database.py
import os
import sqlite3
import pandas as pd
import streamlit as st

DB_PATH = "homicidios.db"
CSV_PATH = "homicidios_completo_limpio.csv"

def actualizar_base_de_datos():
    """
    Lee el CSV limpio y sobrescribe la base de datos SQLite.
    """
    if not os.path.exists(CSV_PATH):
        st.error("❌ No se encontró el archivo CSV para actualizar la base de datos.")
        return False

    try:
        df = pd.read_csv(CSV_PATH)
        # Eliminar columnas basura que a veces genera pandas
        df = df.loc[:, ~df.columns.str.contains("^unnamed", case=False)]
        
        conn = sqlite3.connect(DB_PATH)
        # 'replace' asegura que los datos antiguos se borren y entren los nuevos
        df.to_sql("homicidios", conn, if_exists="replace", index=False)
        conn.close()
        
        # Limpiar el cache de la conexión para que el chat vea los nuevos datos
        get_connection.clear() 
        return True
    except Exception as e:
        st.error(f"⚠️ Error al actualizar SQLite: {e}")
        return False

def crear_db_si_no_existe():
    if os.path.exists(DB_PATH):
        return True
    return actualizar_base_de_datos()

@st.cache_resource
def get_connection():
    if not os.path.exists(DB_PATH):
        return None
    return sqlite3.connect(DB_PATH, check_same_thread=False)

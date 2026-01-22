# -*- coding: utf-8 -*-
import os
import re
import sqlite3
import unicodedata

import pandas as pd
import streamlit as st
import google.generativeai as gen_ai
from dotenv import load_dotenv

def vista_chat():
    if st.button("⬅️ Volver al Dashboard"):
       st.session_state["view"] = "dashboard"
       st.rerun()
       
    # =========================================================
    # Normalización básica (solo para comparar texto)
    # =========================================================
    def normalizar(texto):
        texto = str(texto).lower()
        texto = unicodedata.normalize("NFD", texto)
        texto = texto.encode("ascii", "ignore").decode("utf-8")
        return texto.strip()

    # =========================================================
    # Configuración API Gemini
    # =========================================================
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        st.error("ERROR: GOOGLE_API_KEY no configurada.")
        st.stop()

    gen_ai.configure(api_key=api_key)
    model = gen_ai.GenerativeModel("gemini-2.5-flash")

    # =========================================================
    # Configuración Streamlit
    # =========================================================
    st.set_page_config(page_title="Chat Homicidios IA (SQLite)", layout="wide")
    st.title("🧠 Chat sobre Homicidios (SQLite)")

    # =========================================================
    # Conexión SQLite
    # =========================================================
    DB_PATH = "homicidios.db"

    @st.cache_resource
    def get_connection():
        return sqlite3.connect(DB_PATH, check_same_thread=False)

    conn = get_connection()

    # =========================================================
    # Inicializar historial de chat
    # =========================================================
    if "messages" not in st.session_state:
        st.session_state.messages = [{
            "role": "assistant",
            "content": "¡Hola! Puedes preguntar por homicidios por provincia, año, sexo, tipo de muerte o lugar."
        }]

    # Mostrar historial
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    def motivaciones_mas_frecuentes(conn, provincia):
        query = """
        SELECT presunta_motivacion, COUNT(*) AS total
        FROM homicidios
        WHERE lower(provincia) = lower(?)
          AND presunta_motivacion IS NOT NULL
        GROUP BY presunta_motivacion
        ORDER BY total DESC
        """
        return pd.read_sql_query(query, conn, params=(provincia,))

    def detectar_provincia(pregunta, provincias_disponibles):
        pregunta_norm = normalizar(pregunta)

        for prov in provincias_disponibles:
            if normalizar(prov) in pregunta_norm:
                return prov

        return None


    @st.cache_data
    def get_provincias(_conn):
        query = "SELECT DISTINCT provincia FROM homicidios WHERE provincia IS NOT NULL"
        df = pd.read_sql_query(query, _conn)
        return df["provincia"].tolist()
        
    @st.cache_data
    def get_cantones(_conn):
        # Obtenemos la lista única de cantones para poder compararlos
        query = "SELECT DISTINCT canton FROM homicidios WHERE canton IS NOT NULL"
        df = pd.read_sql_query(query, _conn)
        return df["canton"].tolist()

    def detectar_canton(pregunta, cantones_disponibles):
        pregunta_norm = normalizar(pregunta)
        for canton in cantones_disponibles:
            if normalizar(canton) in pregunta_norm:
                return canton
        return None


    
    def responder_con_gemini(pregunta: str, conn) -> str:
        pregunta_lower = normalizar(pregunta)
        provincias = get_provincias(conn)
        cantones = get_cantones(conn)
        
        where = []
        params = []

        # --- (Detección de Geografía, Año, Sexo, etc. - Se mantiene igual) ---
        provincia_detectada = detectar_provincia(pregunta_lower, provincias)
        pregunta_para_canton = pregunta_lower
        if provincia_detectada:
            where.append("provincia = ?")
            params.append(provincia_detectada)
            pregunta_para_canton = pregunta_para_canton.replace(normalizar(provincia_detectada), "")

        canton_detectado = detectar_canton(pregunta_para_canton, cantones)
        if canton_detectado:
            where.append("canton = ?")
            params.append(canton_detectado)

        match_year = re.search(r'(\d{4})', pregunta_lower)
        if match_year:
            where.append("substr(fecha_infraccion, 1, 4) = ?")
            params.append(match_year.group(1))

        if "mujer" in pregunta_lower:
            where.append("sexo = ?")
            params.append("MUJER")
        elif "hombre" in pregunta_lower:
            where.append("sexo = ?")
            params.append("HOMBRE")

        if "sicariato" in pregunta_lower:
            where.append("tipo_muerte LIKE ?")
            params.append("%SICARIATO%")
        elif "femicidio" in pregunta_lower:
            where.append("tipo_muerte LIKE ?")
            params.append("%FEMICIDIO%")
        # -------------------------------------------------------------------

        where_sql = "WHERE " + " AND ".join(where) if where else ""
        
        # Conteo total para contexto
        total = pd.read_sql_query(f"SELECT COUNT(*) FROM homicidios {where_sql}", conn, params=params).iloc[0, 0]

        if total == 0:
            return "No encontré registros con esos filtros."

        # --- LÓGICA DE DECISIÓN: ¿CASO ESPECÍFICO O ESTADÍSTICA? ---
        
        pide_caso_especifico = any(palabra in pregunta_lower for palabra in ["detalle", "caso", "ejemplo", "cuentame", "cuéntame"])

        if pide_caso_especifico:
            # Buscamos una muestra de 3 casos reales con columnas descriptivas
            query_casos = f"""
                SELECT fecha_infraccion, hora_infraccion, lugar, arma, presunta_motivacion, edad, instruccion
                FROM homicidios 
                {where_sql} 
                ORDER BY RANDOM() LIMIT 3
            """
            df_casos = pd.read_sql_query(query_casos, conn, params=params)
            contexto_datos = "Aquí tienes ejemplos de casos reales individuales:\n" + df_casos.to_json(orient="records", force_ascii=False)
        else:
            # Buscamos el resumen estadístico que ya teníamos
            query_stats = f"SELECT presunta_motivacion, COUNT(*) as total FROM homicidios {where_sql} GROUP BY presunta_motivacion ORDER BY total DESC"
            df_stats = pd.read_sql_query(query_stats, conn, params=params)
            contexto_datos = "Resumen estadístico de motivaciones:\n" + df_stats.to_json(orient="records", force_ascii=False)

        # Prompt único para Gemini
        prompt = f"""
        Eres un experto en criminología y seguridad. 
        Usuario pregunta: "{pregunta}"
        
        Datos del sistema:
        {contexto_datos}
        
        Total de casos en la base de datos para este filtro: {total}
        
        Instrucciones:
        1. Si el usuario pidió un caso o detalle, describe los ejemplos proporcionados con respeto y profesionalismo.
        2. Si el usuario pidió un análisis o estadísticas, usa el resumen para dar una visión global.
        3. Menciona siempre que la información proviene del registro oficial de {total} casos.
        """

        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Error: {e}"

    # =========================================================
    # INPUT DEL CHAT
    # =========================================================



    if prompt := st.chat_input("Haz una pregunta sobre el dataset..."):

        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            placeholder = st.empty()
            placeholder.markdown("Generando respuesta... ⏳")
            respuesta = responder_con_gemini(prompt, conn)
            placeholder.markdown(respuesta)

        st.session_state.messages.append({"role": "assistant", "content": respuesta})

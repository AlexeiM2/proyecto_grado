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


    # =========================================================
    # FUNCIÓN PRINCIPAL (CORREGIDA AL 100%)
    # =========================================================
    def responder_con_gemini(pregunta: str, conn) -> str:
        pregunta_lower = normalizar(pregunta)
        cantidad_solicitada = 20
        provincias = get_provincias(conn)
        provincia_detectada = detectar_provincia(pregunta, provincias)


        # ----------------------------
        # Detectar cantidad solicitada
        # ----------------------------
        m1 = re.search(r'(\d+)\s+primer', pregunta_lower)
        m2 = re.search(r'(\d+)\s+(casos|registros|homicidios|femicidios|asesinatos)', pregunta_lower)
        m3 = re.search(r'(dame|muestrame|muéstrame|quiero)\s+(\d+)', pregunta_lower)

        if m1:
            cantidad_solicitada = int(m1.group(1))
        elif m2:
            cantidad_solicitada = int(m2.group(1))
        elif m3:
            cantidad_solicitada = int(m3.group(2))

        where = []
        params = []

        # ----------------------------
        # Año 
        # ----------------------------
        match_year = re.search(r'(\d{4})', pregunta_lower)
        if match_year:
            where.append("substr(fecha_infraccion, 1, 4) = ?")
            params.append(match_year.group(1))

        # ----------------------------
        # Provincia 
        # ----------------------------
        provincias = pd.read_sql_query(
            "SELECT DISTINCT provincia FROM homicidios WHERE provincia IS NOT NULL",
            conn
        )["provincia"].tolist()

        provincia_detectada = None
        for p in provincias:
            if normalizar(p) in pregunta_lower:
                provincia_detectada = p
                break

        if provincia_detectada:
            where.append("provincia = ?")
            params.append(provincia_detectada)

        if provincia_detectada and any(p in pregunta_lower for p in ["motivacion", "motivaciones"]):

            df_motivaciones = motivaciones_mas_frecuentes(conn, provincia_detectada)

            if df_motivaciones.empty:
                return f"No se encontraron motivaciones registradas para {provincia_detectada}."

            respuesta = f"📊 **Motivaciones más frecuentes en {provincia_detectada}:**\n\n"
            for _, row in df_motivaciones.head(5).iterrows():
                respuesta += f"- {row['presunta_motivacion']}: {row['total']} casos\n"

            return respuesta

        # ----------------------------
        # Tipo de muerte
        # ----------------------------
        if "sicariato" in pregunta_lower:
            where.append("tipo_muerte LIKE ?")
            params.append("%Sicariato%")
        elif "femicidio" in pregunta_lower:
            where.append("tipo_muerte LIKE ?")
            params.append("%Femicidio%")
        elif "asesinato" in pregunta_lower:
            where.append("tipo_muerte = ?")
            params.append("Asesinato")
        elif "tipo de muerte homicidio" in pregunta_lower:
            where.append("tipo_muerte = ?") 
            params.append("Homicidio")

        # ----------------------------
        # Sexo
        # ----------------------------
        if "mujer" in pregunta_lower:
            where.append("sexo = ?")
            params.append("Mujer")
        elif "hombre" in pregunta_lower:
            where.append("sexo = ?")
            params.append("Hombre")

        # ----------------------------
        # Lugar
        # ----------------------------
        if "via publica" in pregunta_lower or "vía publica" in pregunta_lower:
            where.append("lugar LIKE ?")
            params.append("%VIA PUBLICA%")
        elif "domicilio" in pregunta_lower:
            where.append("lugar LIKE ?")
            params.append("%DOMICILIO%")

        # ----------------------------
        # WHERE final
        # ----------------------------
        where_sql = "WHERE " + " AND ".join(where) if where else ""

        # ----------------------------
        # Conteo real (SIN Gemini)
        # ----------------------------
        count_query = f"""
            SELECT COUNT(*) AS total
            FROM homicidios
            {where_sql}
        """
        total = pd.read_sql_query(count_query, conn, params=params).iloc[0, 0]

        if total == 0:
            return "No se encontraron registros que coincidan con la consulta."

        if any(p in pregunta_lower for p in ["cuánt", "cuantos", "cuantas", "total"]):
            return f"Según el dataset, hay **{total} casos** que cumplen los criterios."

        # ----------------------------
        # Obtener muestra
        # ----------------------------
        select_query = f"""
            SELECT *
            FROM homicidios
            {where_sql}
            LIMIT ?
        """
        df_muestra = pd.read_sql_query(
            select_query,
            conn,
            params=params + [cantidad_solicitada]
        )

        if df_muestra.empty:
            return "No se pudieron obtener registros de muestra."

        datos_json = df_muestra.to_json(orient="records", force_ascii=False)

        # ----------------------------
        # Prompt Gemini (solo redacción)
        # ----------------------------
        prompt = f"""
        Eres un asistente experto en análisis de homicidios.
        Responde únicamente con base en los datos reales proporcionados.

        Datos:
        {datos_json}

        Pregunta del usuario: "{pregunta}"
        """

        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Error al generar respuesta: {e}"

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

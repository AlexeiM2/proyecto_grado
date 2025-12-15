# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import google.generativeai as gen_ai
from dotenv import load_dotenv
import os
import re

### UNIFICAR AL DASHBOARD ###

# --- Cargar API KEY desde .env ---
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
if not api_key:
    st.error("ERROR: La variable de entorno GOOGLE_API_KEY no está configurada.")
    st.stop()

gen_ai.configure(api_key=api_key)

# --- Configuración de la página ---
st.set_page_config(page_title="Chat Homicidios IA", layout="wide")
st.title("🧠 Chat sobre Homicidios (CSV restringido)")

# --- Cargar dataset ---
@st.cache_data
def load_data():
    try:
        df = pd.read_csv("homicidios_completo_limpio.csv", parse_dates=["fecha_infraccion"])
        df["año"] = df["fecha_infraccion"].dt.year
        return df
    except FileNotFoundError:
        st.error("ERROR: El archivo 'homicidios_completo_limpio.csv' no fue encontrado.")
        st.stop()

df = load_data()

# --- Inicializar modelo Gemini ---
model = gen_ai.GenerativeModel("gemini-2.5-flash")

# --- Inicializar historial de chat ---
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "¡Hola! ¿Qué datos del dataset de homicidios deseas analizar?"
    }]

# --- Mostrar historial ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])



# =====================================================================
#      FUNCIÓN PRINCIPAL PARA ANALIZAR LA PREGUNTA DEL USUARIO
# =====================================================================
def responder_con_gemini(pregunta, df):
    df_filtrado = df.copy()
    pregunta_lower = pregunta.lower()

    cantidad_solicitada = 20  # valor por defecto

    # Caso 1: “25 primeros”
    match_n1 = re.search(r'(\d+)\s+primer', pregunta_lower)

    # Caso 2: “20 femicidios”, “15 casos”, “12 homicidios”
    match_n2 = re.search(
        r'(\d+)\s+(casos|registros|homicidios|femicidios|asesinatos)',
        pregunta_lower
    )

    # Caso 3: “dame 12”, “muéstrame 15”, “quiero 8”
    match_n3 = re.search(
        r'(dame|muéstrame|quiero)\s+(\d+)',
        pregunta_lower
    )

    if match_n1:
        cantidad_solicitada = int(match_n1.group(1))
    elif match_n2:
        cantidad_solicitada = int(match_n2.group(1))
    elif match_n3:
        cantidad_solicitada = int(match_n3.group(2))


    # ================================================================
    # 🔍 2. APLICAR FILTROS DEL DATASET
    # ================================================================

    # Filtro: año
    match_year = re.search(r'(\d{4})', pregunta_lower)
    if match_year and 'año' in df_filtrado.columns:
        year = int(match_year.group(1))
        df_filtrado = df_filtrado[df_filtrado['año'] == year]

    # Filtro: edad
    match_edad = re.search(r'de (\d{1,2}) años|(\d{1,2}) años', pregunta_lower)
    if match_edad and 'edad' in df_filtrado.columns:
        edad = int(match_edad.group(1) or match_edad.group(2))
        df_filtrado = df_filtrado[df_filtrado['edad'] == edad]

    # Filtro: tipo de muerte
    if 'sicariato' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower().str.contains('sicariato', na=False)]
    elif 'femicidio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower().str.contains('femicidio', na=False)]
    elif 'asesinato' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower() == 'asesinato']
    elif 'homicidio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower() == 'homicidio']

    # Filtro: lugar
    if 'vía pública' in pregunta_lower or 'via publica' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['lugar'].astype(str).str.lower().str.contains('vía pública')]
    if 'domicilio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['lugar'].astype(str).str.lower().str.contains('domicilio')]

    # Filtro: género
    if "mujeres" in pregunta_lower or "mujer" in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['sexo'].str.lower() == 'mujer']
    if "hombres" in pregunta_lower or "hombre" in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['sexo'].str.lower() == 'hombre']

    # Filtros categóricos automáticos
    columnas_a_filtrar = [
        'provincia', 'canton', 'tipo_arma',
        'presunta_motivacion', 'etnia',
        'profesion_registro_civil'
    ]

    for col in columnas_a_filtrar:
        if col in df.columns:
            valores = df[col].dropna().astype(str).str.lower().unique()
            encontrados = [v for v in valores if v in pregunta_lower]
            if encontrados:
                regex = '|'.join(re.escape(p) for p in encontrados)
                df_filtrado = df_filtrado[df_filtrado[col].astype(str).str.lower().str.contains(regex)]


    # ================================================================
    # 🔍 3. SI HAY RESULTADOS
    # ================================================================
    if not df_filtrado.empty:

        # Si es una pregunta de conteo
        if any(p in pregunta_lower for p in ["cuánt", "cuantos", "cuántos", "cuantas", "cuántas", "total"]):
            total = len(df_filtrado)
            return f"Según el dataset, hubo **{total} casos** que coinciden con los criterios mencionados."

        # Obtener los primeros N registros solicitados
        muestra_df = df_filtrado.head(cantidad_solicitada)
        datos_json = muestra_df.to_json(orient="records", force_ascii=False)

        prompt = f"""
        Eres un asistente experto en análisis de homicidios.

        Estos son los **primeros {cantidad_solicitada} registros** filtrados según la consulta:

        {datos_json}

        Pregunta del usuario: "{pregunta}"

        Responde únicamente en base a los datos mostrados.
        """

        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Error al generar la respuesta: {e}"


    # ================================================================
    # 🔍 4. SI NO HUBO RESULTADOS
    # ================================================================
    resumen = f"""
    Dataset de homicidios:
    - Total registros: {len(df)}
    - Años: {df['año'].min()} a {df['año'].max()}
    - Provincias: {df['provincia'].nunique()}
    - Columnas: {', '.join(df.columns)}
    """

    prompt_fallback = f"""
    No se encontraron registros que coincidan con la consulta.

    Resumen del dataset:
    {resumen}

    Pregunta: "{pregunta}"
    """

    response = model.generate_content(prompt_fallback)
    return response.text



# =====================================================================
# CHAT UI
# =====================================================================
if prompt := st.chat_input("Haz una pregunta sobre el dataset..."):

    st.session_state.messages.append({"role": "user", "content": prompt})
    
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("Generando respuesta... ⏳")

        respuesta = responder_con_gemini(prompt, df)
        placeholder.markdown(respuesta)

    st.session_state.messages.append({"role": "assistant", "content": respuesta})


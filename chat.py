import streamlit as st
import pandas as pd
import google.generativeai as gen_ai
from dotenv import load_dotenv
import os
import re

### UNIFICAR AL DASHBOARD ###

# --- Cargar API KEY desde .env ---
load_dotenv()
gen_ai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# --- Configuración de la página ---
st.set_page_config(page_title="Chat Homicidios IA", layout="wide")
st.title("🤖 Chat sobre Homicidios (CSV restringido)")

# --- Cargar dataset ---
@st.cache_data
def load_data():
    df = pd.read_csv("homicidios_completo_limpio.csv", parse_dates=["fecha_infraccion"])
    df["año"] = df["fecha_infraccion"].dt.year
    return df

df = load_data()

# --- Inicializar modelo Gemini ---
model = gen_ai.GenerativeModel("gemini-2.5-flash")

# --- Inicializar historial de chat ---
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Mostrar historial ---
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# --- Función para responder con Gemini con busqueda en el CSV ---

def responder_con_gemini(pregunta, df):
    # Crear una copia del DataFrame para filtrar
    df_filtrado = df.copy()
    pregunta_lower = pregunta.lower()
    
    # Diccionario para mapear términos comunes a nombres de columnas
    mapeo_columnas = {
        'provincia': 'provincia',
        'canton': 'canton',
        'sexo': 'sexo',
        'etnia': 'etnia',
        'lugar': 'lugar',
        'arma': 'tipo_arma',
        'motivacion': 'presunta_motivacion',
        'profesion': 'profesion_registro_civil'
    }

    # Búsqueda por año (números de 4 dígitos)
    match_year = re.search(r'en (\d{4})|del año (\d{4})', pregunta_lower)
    if match_year:
        year = int(match_year.group(1) or match_year.group(2))
        df_filtrado = df_filtrado[df_filtrado['año'] == year]

    # Búsqueda por edad (números de 1 o 2 dígitos)
    match_edad = re.search(r'de (\d{1,2}) años|(\d{1,2}) años', pregunta_lower)
    if match_edad:
        edad = int(match_edad.group(1) or match_edad.group(2))
        df_filtrado = df_filtrado[df_filtrado['edad'] == edad]
    
    # Búsqueda por tipo de muerte
    if 'asesinato' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower() == 'asesinato']
    if 'homicidio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower() == 'homicidio']
    
    # Búsqueda por lugar
    if 'vía pública' in pregunta_lower or 'via publica' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['lugar'].str.lower().str.contains('via publica', na=False)]
    if 'domicilio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['lugar'].str.lower().str.contains('domicilio', na=False)]
    
    # Búsqueda por género/sexo
    if "mujeres" in pregunta_lower or "mujer" in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['sexo'].str.lower() == 'mujer']
    if "hombres" in pregunta_lower or "hombre" in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['sexo'].str.lower() == 'hombre']
        
    # Búsqueda por valores categóricos (provincia, canton, arma, motivación, etc.)
    columnas_a_filtrar = ['provincia', 'canton', 'tipo_arma', 'presunta_motivacion', 'etnia', 'profesion_registro_civil']
    for col in columnas_a_filtrar:
        if col in df.columns:
            valores_unicos = df[col].dropna().unique()
            for valor in valores_unicos:
                if isinstance(valor, str) and valor.lower() in pregunta_lower:
                    df_filtrado = df_filtrado[df_filtrado[col].str.lower().str.contains(valor.lower(), na=False)]

    # Si se encontraron registros, se los pasamos a la IA
    if not df_filtrado.empty:
        # Tomar una muestra aleatoria de hasta 10 registros para evitar exceder el límite de tokens
        muestra_df = df_filtrado.sample(min(10, len(df_filtrado)))
        datos_encontrados_json = muestra_df.to_json(orient='records', force_ascii=False)
        
        prompt = f"""
        Eres un asistente que responde con información de un dataset de homicidios.
        Se encontraron los siguientes datos relevantes para la pregunta del usuario. 
        Analiza este JSON y úsalo para responder de forma clara en español, sintetizando la información.
        
        Datos encontrados:
        {datos_encontrados_json}
        
        Pregunta original: "{pregunta}"

        Responde basándote **únicamente** en los datos JSON proporcionados. 
        Cita campos específicos como el año, la provincia, el tipo de muerte, el sexo y la motivación. Si los datos no son suficientes, indícalo.
        """
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Ocurrió un error al generar la respuesta. Por favor, reformula tu pregunta. (Error: {e})"
    else:
        # Si no se encontró nada, se mantiene la respuesta por defecto
        resumen = f"""
        Dataset de homicidios intencionales:
        - Total registros: {len(df)}
        - Años disponibles: {df['año'].min()} a {df['año'].max()}
        - Provincias únicas: {df['provincia'].nunique()}
        - Columnas: {', '.join(df.columns)}
        """
        
        prompt_fallback = f"""
        Eres un asistente que SOLO puede responder con base en el dataset de homicidios.
        Aquí está el resumen de los datos:
        
        {resumen}
        
        La pregunta del usuario es: "{pregunta}"
        
        Responde de forma clara en español usando únicamente la información contenida en el dataset.
        Si no es posible responder con los datos disponibles, responde:
        "⚠️ No tengo información suficiente en el dataset para responder a eso."
        """
        response = model.generate_content(prompt_fallback)
        return response.text

# --- Caja de entrada ---
if prompt := st.chat_input("Haz una pregunta sobre el dataset..."):
    # Guardar mensaje del usuario
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Respuesta con Gemini
    respuesta = responder_con_gemini(prompt, df)

    # Mostrar respuesta
    with st.chat_message("assistant"):
        st.markdown(respuesta)
    st.session_state.messages.append({"role": "assistant", "content": respuesta})
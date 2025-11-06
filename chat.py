# chat.py
import pandas as pd
import google.generativeai as gen_ai
from dotenv import load_dotenv
import os
import re

# --- Configurar modelo Gemini ---
load_dotenv()
gen_ai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = gen_ai.GenerativeModel("gemini-2.5-flash")

# --- Función principal para responder ---
def responder_con_gemini(pregunta, df):
    df_filtrado = df.copy()
    pregunta_lower = pregunta.lower()
    
    # --- Diccionario de columnas relevantes ---
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

    # --- FILTROS EXACTOS IGUALES A TU CÓDIGO ORIGINAL ---
    # Año
    match_year = re.search(r'en (\d{4})|del año (\d{4})', pregunta_lower)
    if match_year:
        year = int(match_year.group(1) or match_year.group(2))
        df_filtrado = df_filtrado[df_filtrado['año'] == year]

    # Edad
    match_edad = re.search(r'de (\d{1,2}) años|(\d{1,2}) años', pregunta_lower)
    if match_edad:
        edad = int(match_edad.group(1) or match_edad.group(2))
        df_filtrado = df_filtrado[df_filtrado['edad'] == edad]
    
    # Tipo de muerte
    if 'asesinato' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower() == 'asesinato']
    if 'homicidio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['tipo_muerte'].str.lower() == 'homicidio']
    
    # Lugar
    if 'vía pública' in pregunta_lower or 'via publica' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['lugar'].str.lower().str.contains('via publica', na=False)]
    if 'domicilio' in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['lugar'].str.lower().str.contains('domicilio', na=False)]
    
    # Género
    if "mujeres" in pregunta_lower or "mujer" in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['sexo'].str.lower() == 'mujer']
    if "hombres" in pregunta_lower or "hombre" in pregunta_lower:
        df_filtrado = df_filtrado[df_filtrado['sexo'].str.lower() == 'hombre']
        
    # Valores categóricos (provincia, cantón, arma, motivación, etc.)
    columnas_a_filtrar = ['provincia', 'canton', 'tipo_arma', 'presunta_motivacion', 'etnia', 'profesion_registro_civil']
    for col in columnas_a_filtrar:
        if col in df.columns:
            valores_unicos = df[col].dropna().unique()
            for valor in valores_unicos:
                if isinstance(valor, str) and valor.lower() in pregunta_lower:
                    df_filtrado = df_filtrado[df_filtrado[col].str.lower().str.contains(valor.lower(), na=False)]

    # --- DETECTAR SI ES UNA PREGUNTA DE "CUÁNTOS" ---
    if any(palabra in pregunta_lower for palabra in ["cuánt", "cuantos", "cuántos", "cuantas", "cuántas"]):
        total = len(df_filtrado)
        if total > 0:
            respuesta = f"Según el dataset, hubo **{total} homicidios** que coinciden con los criterios mencionados."
        else:
            respuesta = "⚠️ No se encontraron registros que coincidan con los criterios indicados en el dataset."
        return respuesta

    # --- SI NO ES PREGUNTA DE CONTEO, USAR GEMINI ---
    if not df_filtrado.empty:
        muestra_df = df_filtrado.sample(min(10, len(df_filtrado)))
        datos_encontrados_json = muestra_df.to_json(orient='records', force_ascii=False)
        
        prompt = f"""
        Eres un asistente que responde con información de un dataset de homicidios.
        Se encontraron los siguientes datos relevantes para la pregunta del usuario. 
        Analiza este JSON y úsalo para responder de forma clara en español, sintetizando la información.
        
        Datos encontrados:
        {datos_encontrados_json}
        
        Pregunta original: "{pregunta}"

        Responde basándote únicamente en los datos JSON proporcionados. 
        Cita campos específicos como el año, la provincia, el tipo de muerte, el sexo y la motivación. 
        Si los datos no son suficientes, indícalo.
        """
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"⚠️ Error al generar la respuesta con Gemini: {e}"
    else:
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

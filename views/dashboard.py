import streamlit as st
import pandas as pd
import plotly.express as px
import os, glob, re
import unicodedata
from datetime import datetime


# python -m pip install openpyxl

def normalizar_texto(texto):
    if pd.isna(texto) or texto == 'None':
        return None
    # 1. Eliminar tildes y caracteres especiales (NFD descompone caracteres con tilde)
    texto_normalizado = unicodedata.normalize('NFD', str(texto))
    texto_normalizado = texto_normalizado.encode('ascii', 'ignore').decode("utf-8")
    # 2. Quitar espacios extra y pasar a mayúsculas (o Title)
    return texto_normalizado.strip().upper()	

def vista_dashboard():
    if not st.session_state.get("view"):
        st.session_state["view"] = "dashboard"
     
    # Botón para navegar al chat (se mantiene según tu solicitud)
    if st.session_state.get("db_disponible", False):
        if st.button("💬 Ir al Chat Inteligente"):
            st.session_state["view"] = "chat"
            st.rerun()
    else:
        st.info("💡 El chat se habilitará cuando la base de datos SQLite esté disponible.")

    st.set_page_config(page_title="DASHBOARD IA", layout="wide")

    st.title("📊 Dashboard de Homicidios (2014-2025)")


    # --- Función para limpiar y unir archivos Excel ---
    def limpiar_y_unir_archivos(archivos):
        df_list = []
        for archivo in archivos:
            try:
                temp_df = pd.read_excel(archivo, sheet_name=1, header=1)
                df_list.append(temp_df)
            except Exception:
                st.warning(f"No se pudo leer correctamente: {archivo.name}")
        if not df_list:
            return None

        df = pd.concat(df_list, ignore_index=True)
        df.columns = [col.strip().lower().replace(" ", "_").replace(";", "") for col in df.columns]
        df = df.dropna(how='all').drop_duplicates()

        if 'fecha_infraccion' in df.columns:
            df['fecha_infraccion'] = pd.to_datetime(df['fecha_infraccion'], errors='coerce')
            df = df.dropna(subset=['fecha_infraccion'])
            df = df[df['fecha_infraccion'].dt.year >= 2014]

        columnas_texto = [
            'sexo', 'provincia', 'canton', 'tipo_arma', 'arma',
            'presunta_motivacion', 'tipo_muerte', 'etnia', 'estado_civil', 'nacionalidad'
        ]
        for col in columnas_texto:
            if col in df.columns:
                df[col] = df[col].apply(normalizar_texto)

        for col in ['coordenada_x', 'coordenada_y']:
            if col in df.columns:
                df[col] = df[col].astype(str).str.replace("'", "").str.replace(",", ".")
                df[col] = pd.to_numeric(df[col], errors='coerce')
        df.to_csv("homicidios_completo_limpio.csv", index=False)
        return df


    # --- Cargar dataset actual si existe ---
    df = None
    if os.path.exists("homicidios_completo_limpio.csv"):
        df = pd.read_csv("homicidios_completo_limpio.csv", parse_dates=["fecha_infraccion"])
        df['año'] = df['fecha_infraccion'].dt.year

    # --- Sidebar Filtros ---
    if df is not None and not df.empty:
        st.sidebar.header("🔍 Filtros")
        provincias = st.sidebar.multiselect("Provincia", df['provincia'].dropna().unique())
        cantones = st.sidebar.multiselect("Cantón", df['canton'].dropna().unique())
        años = st.sidebar.multiselect("Año", sorted(df['año'].dropna().unique()))
        sexos = st.sidebar.multiselect("Sexo", df['sexo'].dropna().unique())
        tipos_arma = st.sidebar.multiselect("Tipo de Arma", df['tipo_arma'].dropna().unique())
    else:
        provincias = cantones = años = sexos = tipos_arma = []

    # --- Sidebar: Gestión de archivos ---
    with st.sidebar.expander("⚙️ Gestión de Archivos", expanded=False):
        uploaded_files = st.file_uploader(
            "Sube uno o varios archivos Excel (XLSX):",
            accept_multiple_files=True,
            type=["xlsx"]
        )
        if uploaded_files:
            df_new = limpiar_y_unir_archivos(uploaded_files)
            if df_new is not None:
                df_new['año'] = df_new['fecha_infraccion'].dt.year
                st.success("✅ Archivos cargados y limpiados. Refresca la página.")
                st.rerun()

    # --- Aplicar filtros ---
    if df is not None and not df.empty:
        df_filtrado = df.copy()
        if provincias:
            df_filtrado = df_filtrado[df_filtrado['provincia'].isin(provincias)]
        if cantones:
            df_filtrado = df_filtrado[df_filtrado['canton'].isin(cantones)]
        if años:
            df_filtrado = df_filtrado[df_filtrado['año'].isin(años)]
        if sexos:
            df_filtrado = df_filtrado[df_filtrado['sexo'].isin(sexos)]
        if tipos_arma:
            df_filtrado = df_filtrado[df_filtrado['tipo_arma'].isin(tipos_arma)]

        df_filtrado['sexo'] = df_filtrado['sexo'].astype(str).str.upper().str.strip()

        # --- SECCIÓN DASHBOARD (Ahora ocupa todo el ancho) ---
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("💀 Total Homicidios", len(df_filtrado))
        col2.metric("📍 Provincias", df_filtrado['provincia'].nunique())
        col3.metric("🧍‍♀️ Mujeres", (df_filtrado['sexo'] == 'MUJER').sum())
        col4.metric("🧍‍♂️ Hombres", (df_filtrado['sexo'] == 'HOMBRE').sum())

        st.subheader("📅 Homicidios por Año")
        fig1 = px.histogram(df_filtrado, x="año", color="sexo", barmode="group", title="Homicidios por Año y Sexo")
        st.plotly_chart(fig1, use_container_width=True)

        st.subheader("🗺️ Homicidios por Provincia")
        fig2 = px.histogram(df_filtrado, x="provincia", color="sexo", title="Distribución por Provincia")
        st.plotly_chart(fig2, use_container_width=True)

    else:
        st.warning("⚠️ No hay dataset cargado. Sube archivos XLSX para crear el dataset y refresca la app.")
    
    st.divider()

#pip install streamlit pandas plotly


import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Dashboard de Detenidos", layout="wide")

st.title("📊 Dashboard Interactivo de Detenidos y Aprehendidos (2020-2025)")

# Cargar el dataset limpio
@st.cache_data
def cargar_datos():
    df = pd.read_csv("detenidos_completo_limpio.csv", parse_dates=["fecha_detencion_aprehension"])
    df['año'] = df['fecha_detencion_aprehension'].dt.year
    return df

df = cargar_datos()

# Filtros interactivos
st.sidebar.header("🔍 Filtros")

provincias = st.sidebar.multiselect("Provincia", df['nombre_provincia'].dropna().unique())
cantones = st.sidebar.multiselect("Cantón", df['nombre_canton'].dropna().unique())
años = st.sidebar.multiselect("Año", sorted(df['año'].dropna().unique()))
sexos = st.sidebar.multiselect("Sexo", df['sexo'].dropna().unique())
tipos_arma = st.sidebar.multiselect("Tipo de Arma", df['tipo_arma'].dropna().unique())

# Aplicar filtros
df_filtrado = df.copy()
if provincias:
    df_filtrado = df_filtrado[df_filtrado['nombre_provincia'].isin(provincias)]
if cantones:
    df_filtrado = df_filtrado[df_filtrado['nombre_canton'].isin(cantones)]
if años:
    df_filtrado = df_filtrado[df_filtrado['año'].isin(años)]
if sexos:
    df_filtrado = df_filtrado[df_filtrado['sexo'].isin(sexos)]
if tipos_arma:
    df_filtrado = df_filtrado[df_filtrado['tipo_arma'].isin(tipos_arma)]

# KPIs
col1, col2, col3 = st.columns(3)
col1.metric("👮‍♂️ Total Detenidos", len(df_filtrado))
col2.metric("📍 Provincias", df_filtrado['nombre_provincia'].nunique())
col3.metric("🧍‍♀️ Mujeres", (df_filtrado['sexo'] == 'a').sum())
# Gráfico 1: Detenidos por año
st.subheader("📅 Detenidos por Año")
fig1 = px.histogram(df_filtrado, x="año", color="sexo", barmode="group", title="Detenciones por Año y Sexo")
st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2: Detenidos por Provincia
st.subheader("🗺️ Detenidos por Provincia")
fig2 = px.histogram(df_filtrado, x="nombre_provincia", color="sexo", title="Distribución por Provincia")
st.plotly_chart(fig2, use_container_width=True)

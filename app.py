# pip install streamlit pandas plotly

import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="DASHBOARD IA", layout="wide")

st.title("📊 Dashboard de Homicidios Intencionales (2014-2025)")

# Cargar el dataset limpio
@st.cache_data
def cargar_datos():
    df = pd.read_csv("homicidios_completo_limpio.csv", parse_dates=["fecha_infraccion"])
    df['año'] = df['fecha_infraccion'].dt.year
    return df

df = cargar_datos()

# Filtros interactivos
st.sidebar.header("🔍 Filtros")

provincias = st.sidebar.multiselect("Provincia", df['provincia'].dropna().unique())
cantones = st.sidebar.multiselect("Cantón", df['canton'].dropna().unique())
años = st.sidebar.multiselect("Año", sorted(df['año'].dropna().unique()))
sexos = st.sidebar.multiselect("Sexo", df['sexo'].dropna().unique())
tipos_arma = st.sidebar.multiselect("Tipo de Arma", df['tipo_arma'].dropna().unique())

# Aplicar filtros
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

# Normalizar el texto en la columna 'sexo'
df_filtrado['sexo'] = df_filtrado['sexo'].astype(str).str.upper().str.strip()

# KPIs
col1, col2, col3, col4 = st.columns(4)
col1.metric("💀 Total Homicidios", len(df_filtrado))
col2.metric("📍 Provincias", df_filtrado['provincia'].nunique())
col3.metric("🧍‍♀️ Mujeres", (df_filtrado['sexo'] == 'MUJER').sum())
col4.metric("🧍‍♂️ Hombres", (df_filtrado['sexo'] == 'HOMBRE').sum())

# Gráfico 1: Homicidios por año
st.subheader("📅 Homicidios por Año")
fig1 = px.histogram(df_filtrado, x="año", color="sexo", barmode="group", title="Homicidios por Año y Sexo")
st.plotly_chart(fig1, use_container_width=True)

# Gráfico 2: Homicidios por Provincia
st.subheader("🗺️ Homicidios por Provincia")
fig2 = px.histogram(df_filtrado, x="provincia", color="sexo", title="Distribución por Provincia")
st.plotly_chart(fig2, use_container_width=True)

# app.py
import streamlit as st
from database import crear_db_si_no_existe
from views.dashboard import vista_dashboard
from views.chat import vista_chat

st.set_page_config(page_title="Homicidios IA", layout="wide")

# Intentar crear DB (NO obligatorio)
db_disponible = crear_db_si_no_existe()

# Guardar estado global
st.session_state["db_disponible"] = db_disponible

# Vista por defecto
if "view" not in st.session_state:
    st.session_state["view"] = "dashboard"

# Router
if st.session_state["view"] == "dashboard":
    vista_dashboard()
elif st.session_state["view"] == "chat":
    if st.session_state.get("db_disponible", False):
        vista_chat()
    else:
        st.warning("⚠️ El chat no está disponible porque no existe la base de datos.")
        st.session_state["view"] = "dashboard"
        st.rerun()

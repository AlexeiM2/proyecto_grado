#pip install pandas openpyxl

import pandas as pd

# Rutas de los archivos Excel
archivos = [
    "mdi_detenidos-aprehendidos_pm_2019_2024.xlsx",
    "mdi_detenidosaprehendidos_pm_ene_jun_2025.xlsx"
]


# Cargar y concatenar la SEGUNDA HOJA de cada archivo
# Leer la segunda hoja de cada archivo y usar la segunda fila como encabezado (header=1)
df_list = [
    pd.read_excel(archivo, sheet_name=1, header=1) for archivo in archivos
]

# Unificar los archivos
df = pd.concat(df_list, ignore_index=True)

# Normalizar nombres de columnas
df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]

# Eliminar filas completamente vacías
df = df.dropna(how='all')

# Eliminar duplicados
df = df.drop_duplicates()

# Convertir fecha de detención si existe
if 'fecha_detencion_aprehension' in df.columns:
    df['fecha_detencion_aprehension'] = pd.to_datetime(df['fecha_detencion_aprehension'], errors='coerce')
    df = df.dropna(subset=['fecha_detencion_aprehension'])
    df = df[df['fecha_detencion_aprehension'].dt.year >= 2020]

# Limpiar valores de texto clave
for col in ['sexo', 'nombre_provincia', 'tipo_arma', 'presunta_infraccion']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.title().str.strip()

# Guardar dataset limpio completo
df.to_csv("detenidos_completo_limpio.csv", index=False)

print("✅ Dataset completo y limpio guardado como 'detenidos_completo_limpio.csv'")
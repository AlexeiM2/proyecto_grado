#pip install pandas openpyxl

import pandas as pd

# Rutas de los archivos Excel
archivos = [
    r"C:\Users\Lenovo\Documents\proyecto_grado\mdi_homicidios_intencionales_pm_2025_ene_jun.xlsx",
    r"C:\Users\Lenovo\Documents\proyecto_grado\mdi_homicidios_intencionales_pm_2014_2024.xlsx"
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
if 'fecha_infraccion' in df.columns:
    df['fecha_infraccion'] = pd.to_datetime(df['fecha_infraccion'], errors='coerce')
    df = df.dropna(subset=['fecha_infraccion'])
    df = df[df['fecha_infraccion'].dt.year >= 2020]

# Limpiar valores de texto clave
for col in ['sexo', 'provincia', 'tipo_arma', 'presunta_motivacion']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.title().str.strip()

# Guardar dataset limpio completo
df.to_csv("homicidios_completo_limpio.csv", index=False)

print(" Dataset completo y limpio guardado como 'homicidios_completo_limpio.csv'")
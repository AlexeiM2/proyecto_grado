import pandas as pd

# Archivos corregidos
archivos = [
    "mdi_homicidios_intencionales_pm_2014_2024.xlsx",
    "mdi_homicidios_intencionales_pm_2025_ene_jun.xlsx"
]

# Leer hoja correcta con encabezado real (ajustar si está en otra hoja o fila)
df_list = [pd.read_excel(archivo, sheet_name=1, header=1) for archivo in archivos]

# Concatenar los DataFrames
df = pd.concat(df_list, ignore_index=True)

# Normalizar nombres de columnas
df.columns = [col.strip().lower().replace(" ", "_").replace(";", "") for col in df.columns]

# Eliminar filas vacías y duplicados
df = df.dropna(how='all').drop_duplicates()

# Convertir fecha de infracción
if 'fecha_infraccion' in df.columns:
    df['fecha_infraccion'] = pd.to_datetime(df['fecha_infraccion'], errors='coerce')
    df = df.dropna(subset=['fecha_infraccion'])
    df = df[df['fecha_infraccion'].dt.year >= 2014] 

# Limpiar columnas clave si existen
columnas_texto = [
    'sexo', 'provincia', 'canton', 'tipo_arma', 'arma',
    'presunta_motivacion', 'tipo_muerte', 'etnia', 'estado_civil', 'nacionalidad'
]

for col in columnas_texto:
    if col in df.columns:
        df[col] = df[col].astype(str).str.title().str.strip()

# Convertir coordenadas a float (si tienen comillas)
for col in ['coordenada_x', 'coordenada_y']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace("'", "").str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Guardar dataset limpio
df.to_csv("homicidios_completo_limpio.csv", index=False)
print("✅ Dataset limpio guardado como 'homicidios_completo_limpio.csv'")

import pandas as pd

# Cargar el nuevo archivo CSV de homicidios
df = pd.read_csv("homicidios_completo_limpio.csv")

# Eliminar columna de índice si existe
if 'unnamed:_0' in df.columns:
    df = df.drop(columns=['unnamed:_0'])

# Asegurarse de que la fecha esté bien formateada
if 'fecha_infraccion' in df.columns:
    df['fecha_infraccion'] = pd.to_datetime(df['fecha_infraccion'], errors='coerce')

# Normalizar texto en columnas clave (si existen)
for col in ['sexo', 'tipo_muerte', 'provincia', 'canton', 'tipo_arma', 'arma', 'presunta_motivacion', 'nacionalidad']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.title().str.strip()

# Limpiar coordenadas (quitar comillas, convertir a float)
for col in ['coordenada_x', 'coordenada_y']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace("'", "").str.replace(",", ".")
        df[col] = pd.to_numeric(df[col], errors='coerce')

# Guardar archivo limpio final
df.to_csv("homicidios_completo_limpio.csv", index=False)

print("✅ Archivo final limpio y listo para usar: 'homicidios_completo_limpio.csv'")

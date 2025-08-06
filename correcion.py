import pandas as pd

# Cargar el CSV generado previamente
df = pd.read_csv("homicidios_completo_limpio.csv")

# Eliminar columna de índice si existe
if 'unnamed:_0' in df.columns:
    df = df.drop(columns=['unnamed:_0'])

# Asegurarse de que fechas estén bien formateadas
df['fecha_infraccion'] = pd.to_datetime(df['fecha_infraccion'], errors='coerce')

# Normalizar texto en algunas columnas clave
for col in ['sexo', 'tipo_muerte', 'nombre_provincia', 'nombre_canton', 'nombre_parroquia', 'tipo_arma', 'presunta_motivacion']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.title().str.strip()

# Opcional: quitar comillas de latitud/longitud si están como string con comillas simples
for col in ['latitud', 'longitud']:
    if col in df.columns:
        df[col] = df[col].astype(str).str.replace("'", "").astype(float)

# Guardar el CSV limpio y listo para visualización
df.to_csv("homicidios_completo_limpio.csv", index=False)

print("Archivo final limpio y listo para usar: 'homicidios_completo_limpio.csv'")

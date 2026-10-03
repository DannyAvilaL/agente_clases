import os
import pandas as pd
from sqlalchemy import create_engine, inspect
from dotenv import load_dotenv

load_dotenv(dotenv_path='config/.env')

def obtener_conexion_db():
    usuario = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")
    host = os.getenv("DB_HOST")
    puerto = os.getenv("DB_PORT")
    bd = os.getenv("DB_NAME")
    return create_engine(f'postgresql+psycopg2://{usuario}:{password}@{host}:{puerto}/{bd}')

def subir_dataset_a_postgres(dataframe, nombre_tabla):
    motor = obtener_conexion_db()
    try:
        dataframe.to_sql(nombre_tabla, motor, if_exists='replace', index=False)
        return True
    except Exception as e:
        print(f"Error subiendo a BD: {e}")
        return False

def obtener_tablas_existentes():
    """Devuelve una lista con los nombres de las tablas actuales en la BD."""
    try:
        motor = obtener_conexion_db()
        inspector = inspect(motor)
        tablas = inspector.get_table_names()
        return tablas if tablas else ["Ninguna tabla disponible aún."]
    except Exception as e:
        print(f"Error conectando a BD para leer tablas: {e}")
        return ["Error leyendo la base de datos."]
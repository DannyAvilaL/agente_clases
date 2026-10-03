import os
import json
import datetime
from datetime import timedelta
import requests
import caldav
import re
import pandas as pd
import io

# modulos personalizados
import db_utils 
from costos import calcular_costo_tokens, medir_tiempo_ejecucion

from dotenv import load_dotenv
load_dotenv(dotenv_path='config/.env')


RADICALE_URL = os.getenv("RADICALE_URL")
RADICALE_USER = os.getenv("RADICALE_USER")
RADICALE_PASS = os.getenv("RADICALE_PASS")

RUTA_JSON = os.getenv("RUTA_JSON")
RUTA_GENERADOS = "data/generados/"
OLLAMA_URL = os.getenv("OLLAMA_HOST")

def obtener_clases_proxima_semana():
    fecha_objetivo = datetime.datetime.now() + timedelta(days=0)
    print(f"📅 Leyendo calendario para el: {fecha_objetivo.strftime('%Y-%m-%d')}...")
    
    try:
        client = caldav.DAVClient(url=RADICALE_URL, username=RADICALE_USER, password=RADICALE_PASS)
        principal = client.principal()
        calendario_local = principal.calendar(name="Clases")
        
        inicio_dia = fecha_objetivo.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = fecha_objetivo.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        eventos = calendario_local.search(start=inicio_dia, end=fin_dia)
        clases_futuras = [str(e.icalendar_component.get("summary")) for e in eventos]
            
        return clases_futuras, fecha_objetivo
    except Exception as e:
        print(f"❌ Error al conectar con Radicale: {e}")
        return [], fecha_objetivo

def leer_progreso_alumno(nombre_evento):
    try:
        with open(RUTA_JSON, 'r', encoding='utf-8') as f:
            datos = json.load(f)
            for id_curso, info in datos.items():
                if nombre_evento == id_curso or nombre_evento in info.get("eventos_vinculados", []):
                    return info
            return None
    except FileNotFoundError:
        return None

def generar_material_con_ollama(info_alumno, nombre_evento, tablas_bd):
    temas_vistos = ", ".join(info_alumno.get("temas_vistos", []))
    tema_nuevo = info_alumno.get("tema_siguiente", "Tema general")
    nivel = info_alumno.get("nivel", "básico")
    intereses = info_alumno.get("intereses", "programación")
    alumno = info_alumno.get("alumno", "Alumno")
    
    # Contexto de la base de datos en el prompt
    prompt = f"""
    Eres un profesor de programación y análisis de datos preparando una clase para '{alumno}'.
    Tema nuevo: '{tema_nuevo}'. Nivel: {nivel}. Intereses: {intereses}.
    Temas que ya domina: {temas_vistos}.
    
    Actualmente, nuestra base de datos PostgreSQL local tiene estas tablas: {tablas_bd}.
    
    Por favor genera un documento en Markdown con:
    1. Una explicación de '{tema_nuevo}'.
    2. Tres ejemplos de código en Python. Si es relevante, formula consultas o usa Pandas asumiendo que existen las tablas actuales.
    3. Una lista de 10 ejercicios prácticos con duración de ejecución total de 1 hora.
    4. OBLIGATORIO: Genera un nuevo dataset sintético (máximo 15 filas) relacionado con sus intereses para un nuevo ejercicio. 
       Debes entregar este dataset EXACTAMENTE dentro de un bloque de código marcado como ```csv y con encabezados.
    """

    print(f"🧠 Solicitando generación a Ollama para el tema: {tema_nuevo}...")
    
    payload = {"model": "phi3:mini ", 
               "prompt": prompt, 
               "stream": False, 
               "options": {"temperature": 0.2}}
    try:
        response, tiempo_ejecucion = medir_tiempo_ejecucion(
            requests.post, OLLAMA_URL, json=payload
        )
        response.raise_for_status()
        resultado = response.json()

        tokens_entrada = resultado.get("prompt_eval_count")
        tokens_salida = resultado.get("eval_count")
        if isinstance(tokens_entrada, int) and isinstance(tokens_salida, int):
            costo = calcular_costo_tokens(tokens_entrada, tokens_salida)
            print(
                f"📊 Tokens: {tokens_entrada} de entrada, {tokens_salida} de salida. "
                f"Costo local: {costo:.8f}."
            )
        print(f"⏱️ Tiempo de ejecución del modelo: {tiempo_ejecucion:.2f} s.")
        return resultado.get("response", "")
    except requests.exceptions.RequestException as e:
        print(f"❌ Error con Ollama: {e}")
        return ""

def procesar_respuesta_y_bd(texto_ollama, nombre_clase):
    if not os.path.exists(RUTA_GENERADOS):
        os.makedirs(RUTA_GENERADOS)
        
    fecha = datetime.datetime.now().strftime("%Y-%m-%d")
    nombre_base = f"Clase_{nombre_clase.replace(' ', '_')}_{fecha}"
    nombre_md = f"{nombre_base}.md"
    nombre_csv = f"{nombre_base}.csv"
    
    # 1. Guardar el archivo Markdown
    with open(f"{RUTA_GENERADOS}{nombre_md}", 'w', encoding='utf-8') as f:
        f.write(texto_ollama)
    print(f"✅ Material Markdown guardado: {nombre_md}")

    # 2. Buscar el bloque CSV en la respuesta de Ollama
    match = re.search(r'```csv\n(.*?)\n```', texto_ollama, re.DOTALL | re.IGNORECASE)
    
    if match:
        datos_csv = match.group(1).strip()
        
        # 3. Guardar el archivo .csv físicamente para descarga
        with open(f"{RUTA_GENERADOS}{nombre_csv}", 'w', encoding='utf-8') as f:
            f.write(datos_csv)
        print(f"✅ Archivo CSV generado y listo para usar: {nombre_csv}")
        
        # 4. Inyectar los datos en PostgreSQL
        try:
            df = pd.read_csv(io.StringIO(datos_csv))
            nombre_tabla = f"dataset_{nombre_clase.replace(' ', '_').lower()}"
            
            exito = db_utils.subir_dataset_a_postgres(df, nombre_tabla)
            if exito:
                print(f"💾 Dataset subido a PostgreSQL en la tabla: '{nombre_tabla}'")
        except Exception as e:
            print(f"⚠️ Error procesando el CSV para la BD: {e}")
    else:
        print("⚠️ Ollama no generó un bloque de código CSV válido.")

def main():
    print("Iniciando Agente Tutor Local (Conexión BD)...")
    eventos, fecha_objetivo = obtener_clases_proxima_semana()
    
    if not eventos:
        print(f"No hay clases para el {fecha_objetivo.strftime('%Y-%m-%d')}.")
        return

    # Consulta del estado de la BD local antes de procesar las clases
    tablas_bd = db_utils.obtener_tablas_existentes()
    print(f"📊 Tablas detectadas en PostgreSQL: {tablas_bd}")

    for nombre_evento in eventos:
        print(f"\n--- Preparando material para: {nombre_evento} ---")
        info_alumno = leer_progreso_alumno(nombre_evento)
        
        if info_alumno:
            material = generar_material_con_ollama(info_alumno, nombre_evento, tablas_bd)
            if material:
                procesar_respuesta_y_bd(material, nombre_evento)
        else:
            print(f"⚠️ Sin registro en {RUTA_JSON} para '{nombre_evento}'")

if __name__ == '__main__':
    main()
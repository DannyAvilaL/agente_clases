import streamlit as st
import json
import os
import glob
import caldav
from icalendar import Calendar, Event
from datetime import datetime, timedelta
import uuid
from dotenv import load_dotenv

# --- FUNCIONES AUXILIARES ---
ARCHIVO_JSON = 'data/alumnos.json'
# --- CONFIGURACIÓN DE RADICALE ---
load_dotenv(dotenv_path='config/.env')

RADICALE_URL = os.getenv("RADICALE_URL")
RADICALE_USER = os.getenv("RADICALE_USER")
RADICALE_PASS = os.getenv("RADICALE_PASS")

def cargar_datos():
    """Lee el archivo JSON con los datos de los alumnos."""
    if os.path.exists(ARCHIVO_JSON):
        with open(ARCHIVO_JSON, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def guardar_datos(datos):
    """Guarda los cambios en el archivo JSON."""
    with open(ARCHIVO_JSON, 'w', encoding='utf-8') as f:
        json.dump(datos, f, indent=4, ensure_ascii=False)

def obtener_alumno_por_archivo(ruta_archivo, datos):
    """Extrae el nombre de la clase del archivo y busca a qué alumno le pertenece."""
    nombre_base = os.path.basename(ruta_archivo)
    
    # El formato es: Clase_Nombre_de_la_Clase_2026-10-07.md
    if nombre_base.startswith("Clase_") and nombre_base.endswith(".md"):
        # Quitamos 'Clase_' (primeros 6 chars) y '.md' (últimos 3)
        nucleo = nombre_base[6:-3]
        # Separamos la fecha, que es el último bloque después del último guión bajo
        partes = nucleo.rsplit('_', 1)
        
        if len(partes) == 2:
            clase_archivo = partes[0]
            
            # Buscar coincidencia en alumnos.json
            for id_curso, info in datos.items():
                if id_curso.replace(' ', '_') == clase_archivo:
                    return info.get("alumno", "Desconocido")
                # Revisar también en eventos vinculados
                for evento in info.get("eventos_vinculados", []):
                    if evento.replace(' ', '_') == clase_archivo:
                        return info.get("alumno", "Desconocido")
                        
    return "Sin asignar"

def subir_evento_radicale(ical_data):
    """Sube un string en formato ICS directamente a Radicale."""
    client = caldav.DAVClient(url=RADICALE_URL, username=RADICALE_USER, password=RADICALE_PASS)
    principal = client.principal()
    try:
        calendario_local = principal.calendar(name="Clases")
    except caldav.error.NotFoundError:
        calendario_local = principal.make_calendar(name="Clases")
    calendario_local.save_event(ical_data)

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Tutor Inteligente", page_icon="👨‍🏫", layout="wide")
st.title("👨‍🏫 Panel de Control - Tutor Inteligente")

# Crear dos pestañas en la interfaz
tab1, tab2, tab3 = st.tabs(["📚 Actualizar Temario", "📄 Ver Materiales", "📅 Agenda Local (Offline)"])

# ==========================================
# PESTAÑA 1: ACTUALIZAR PROGRESO DEL ALUMNO
# ==========================================
with tab1:
    st.header("Gestión de Alumnos y Temarios")
    datos = cargar_datos()
    
    if not datos:
        st.warning(f"No se encontró el archivo {ARCHIVO_JSON}. Agrega una clase para comenzar.")
        datos = {}

    # Selector de clases existentes o opción para crear una nueva
    opciones_clases = list(datos.keys()) + ["+ Crear nueva clase..."]
    clase_seleccionada = st.selectbox("Selecciona la clase o evento del calendario:", opciones_clases)

    if clase_seleccionada == "+ Crear nueva clase...":
        clase_editar = st.text_input("Nombre exacto del evento en Google Calendar (Ej. Clase Sabados 9am):")
        info = {"alumno": "", "temas_vistos": [], "tema_siguiente": "", "nivel": "", "intereses": ""}
    else:
        clase_editar = clase_seleccionada
        info = datos[clase_seleccionada]

    # Formulario para editar la información
    if clase_editar:
        with st.form("form_edicion"):
            st.subheader(f"Datos para: {clase_editar}")
            
            nuevo_alumno = st.text_input("Nombre del Alumno", info.get("alumno", ""))
            
            # Los temas vistos son una lista, los unimos con comas para que sean fáciles de editar
            str_temas_vistos = ", ".join(info.get("temas_vistos", []))
            nuevos_temas = st.text_area("Temas ya vistos (separados por coma)", str_temas_vistos, 
                                        help="Ej: metodos de string, condicionales if/else, ciclos")
            
            nuevo_tema_sig = st.text_input("Siguiente tema a enseñar", info.get("tema_siguiente", ""))
            
            col1, col2 = st.columns(2)
            with col1:
                nuevo_nivel = st.text_input("Nivel", info.get("nivel", ""))
            with col2:
                nuevos_intereses = st.text_input("Intereses", info.get("intereses", ""))
            
            submitted = st.form_submit_button("💾 Guardar Cambios")
            
            if submitted:
                # Volver a convertir el string de temas a una lista de Python
                lista_temas = [t.strip() for t in nuevos_temas.split(",") if t.strip()]
                
                # Actualizar el diccionario y guardar
                datos[clase_editar] = {
                    "alumno": nuevo_alumno,
                    "temas_vistos": lista_temas,
                    "tema_siguiente": nuevo_tema_sig,
                    "nivel": nuevo_nivel,
                    "intereses": nuevos_intereses
                }
                guardar_datos(datos)
                st.success("¡Datos actualizados correctamente en alumnos.json!")
                st.rerun() # Recargar la app para mostrar los cambios

# ==========================================
# PESTAÑA 2: VISOR DE ARCHIVOS MARKDOWN Y CSV
# ==========================================
with tab2:
    st.header("Materiales de Clase Generados")
    
    RUTA_GENERADOS = "data/generados/"
    archivos_md = glob.glob(f"{RUTA_GENERADOS}*.md")
    
    # 1. Cargar datos para saber qué alumnos existen en total
    datos_alumnos = cargar_datos()
    
    # Extraer TODOS los alumnos registrados en alumnos.json
    todos_los_alumnos = set()
    if datos_alumnos:
        for info in datos_alumnos.values():
            nombre_alumno = info.get("alumno", "").strip()
            if nombre_alumno:
                todos_los_alumnos.add(nombre_alumno)
                
    # 2. Clasificar los archivos existentes por alumno
    archivos_por_alumno = {}
    if archivos_md:
        archivos_md.sort(key=os.path.getmtime, reverse=True)
        for archivo in archivos_md:
            alumno = obtener_alumno_por_archivo(archivo, datos_alumnos)
            if alumno not in archivos_por_alumno:
                archivos_por_alumno[alumno] = []
            archivos_por_alumno[alumno].append(archivo)
            
        # Si hay archivos huérfanos o de "Desconocido", los agregamos a la lista de opciones
        todos_los_alumnos.update(archivos_por_alumno.keys())
        
    # 3. Construir el selector de filtro con TODOS los alumnos
    lista_alumnos = ["Todos"] + sorted(list(todos_los_alumnos))
    filtro_alumno = st.selectbox("Filtra los materiales por alumno:", lista_alumnos)
    
    # 4. Aplicar el filtro a la vista
    if filtro_alumno == "Todos":
        archivos_a_mostrar = archivos_md
    else:
        # Usamos .get() por si el alumno seleccionado aún no tiene archivos
        archivos_a_mostrar = archivos_por_alumno.get(filtro_alumno, [])
        
    # 5. Renderizar los resultados
    if not archivos_a_mostrar:
        st.info(f"Aún no hay materiales generados para {filtro_alumno if filtro_alumno != 'Todos' else 'ningún alumno'}.")
    else:
        col_select, col_visor = st.columns([1, 3])
        
        with col_select:
            # Mostrar solo el nombre del archivo para que sea legible
            nombres_display = {os.path.basename(ruta): ruta for ruta in archivos_a_mostrar}
            archivo_seleccionado_nombre = st.radio("Selecciona un archivo:", list(nombres_display.keys()))
            archivo_seleccionado_ruta = nombres_display[archivo_seleccionado_nombre]
        
        with col_visor:
            st.subheader(f"Visualizando material para: {filtro_alumno if filtro_alumno != 'Todos' else 'Varios'}")
            st.markdown(f"**Archivo:** `{archivo_seleccionado_nombre}`")
            st.markdown("---")
            
            # Renderizar el contenido Markdown
            with open(archivo_seleccionado_ruta, 'r', encoding='utf-8') as f:
                contenido = f.read()
            st.markdown(contenido)
            
            # Botón de descarga para el CSV sintético
            ruta_csv = archivo_seleccionado_ruta.replace('.md', '.csv')
            if os.path.exists(ruta_csv):
                with open(ruta_csv, 'rb') as f:
                    st.download_button(
                        label="📥 Descargar Dataset Sintético (.csv)",
                        data=f,
                        file_name=os.path.basename(ruta_csv),
                        mime="text/csv"
                    )

# ==========================================
# PESTAÑA 3: AGENDA LOCAL (OFFLINE)
# ==========================================
with tab3:
    st.header("Gestión del Calendario Local")
    st.info("Si no tienes internet para sincronizar con Google, puedes agregar eventos directamente a tu servidor Radicale desde aquí.")
    
    col_upload, col_manual = st.columns(2)
    
    # OPCIÓN A: Cargar archivo .ics
    with col_upload:
        st.subheader("📁 Opción 1: Subir archivo .ics")
        st.write("Exporta un evento desde Thunderbird, Apple Calendar o Outlook e impórtalo aquí.")
        archivo_ics = st.file_uploader("Selecciona el archivo", type=['ics'])
        
        if st.button("Subir Eventos del Archivo"):
            if archivo_ics is not None:
                contenido_ics = archivo_ics.getvalue().decode('utf-8')
                try:
                    subir_evento_radicale(contenido_ics)
                    st.success("¡Eventos cargados exitosamente a Radicale!")
                except Exception as e:
                    st.error(f"Error al procesar el archivo: {e}")
            else:
                st.warning("Por favor, sube un archivo primero.")

    # OPCIÓN B: Crear evento manual
    with col_manual:
        st.subheader("✍️ Opción 2: Crear clase manualmente")
        
        # Sugerir nombres de las clases que ya existen en el JSON
        datos = cargar_datos()
        opciones_titulos = list(datos.keys()) if datos else ["Clase Python"]
        
        titulo_clase = st.text_input("Título de la clase", value=opciones_titulos[0])
        fecha_clase = st.date_input("Fecha de la clase")
        hora_clase = st.time_input("Hora de inicio")
        duracion_horas = st.number_input("Duración (horas)", min_value=1, max_value=5, value=1)
        
        if st.button("Guardar Clase en Calendario"):
            # Generar la estructura del evento iCalendar (ICS)
            cal = Calendar()
            cal.add('prodid', '-//Tutor Agent Local//mxm.dk//')
            cal.add('version', '2.0')
            
            evento = Event()
            evento.add('uid', str(uuid.uuid4()))
            evento.add('summary', titulo_clase)
            
            # Combinar fecha y hora
            inicio = datetime.combine(fecha_clase, hora_clase)
            fin = inicio + timedelta(hours=duracion_horas)
            
            evento.add('dtstart', inicio)
            evento.add('dtend', fin)
            cal.add_component(evento)
            
            try:
                subir_evento_radicale(cal.to_ical())
                st.success(f"Clase '{titulo_clase}' agendada para el {fecha_clase.strftime('%d/%m/%Y')}.")
            except Exception as e:
                st.error(f"Error al guardar el evento: {e}")
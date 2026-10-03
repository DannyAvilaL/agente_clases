# 👨‍🏫 Tutor Agente Local (AI Teaching Assistant)

Un ecosistema local impulsado por Inteligencia Artificial diseñado para automatizar la preparación de clases de programación. El agente funciona 100% offline en WSL, gestiona un calendario local, rastrea el progreso individual de los alumnos y utiliza modelos LLM locales (vía Ollama) para generar material didáctico hiper-personalizado, ejercicios y datasets sintéticos inyectados directamente en PostgreSQL.

Tiene la posibilidad de conectarse y sincronizarse con el calendario de Google a través de la API por medio del token y credenciales generados para el escenario donde sí exista una conexión a internet.

## ✨ Características Principales

* **Generación de Clases con IA:** Crea explicaciones detalladas y ejemplos de código en formato Markdown adaptados al nivel, intereses y temas previos del alumno.
* **Datos Sintéticos Automatizados:** Genera datasets en formato `.csv` a medida para los ejercicios, los guarda para su descarga y los inyecta automáticamente como tablas en una base de datos PostgreSQL local.
* **Local-First con Cloud Sync:** Sincroniza eventos desde Google Calendar hacia un servidor CalDAV local (Radicale). Si no hay internet, el sistema sigue funcionando al 100% con la agenda local.
* **Panel de Control (Dashboard):** Interfaz web construida con Streamlit para actualizar el temario de los alumnos, filtrar y visualizar los materiales generados, descargar los CSVs y agendar clases manualmente sin conexión.
* **Piloto Automático:** Preparado para ejecutarse mediante `cron`, preparando las clases con una semana de anticipación de forma totalmente autónoma.

---

## 🛠️ Tecnologías Utilizadas

* **Lenguaje:** Python 3
* **LLM Local:** Ollama modelo Phi-3 (2 GB)
* **Base de Datos:** PostgreSQL (para datasets) y JSON (para progreso de alumnos)
* **Calendario:** Radicale (Servidor CalDAV local) e iCalendar
* **Interfaz:** Streamlit
* **Librerías Clave:** `pandas`, `sqlalchemy`, `caldav`, `google-api-python-client`, `requests`

## Hardware Utilizado

* **CPU:** Intel Core i7-118000H @ 2.3GHz con 8 cores
* **Memoria RAM:** 32 GB SODIMM a velocidad 3200MT/s
* **GPU:** NVIDIA GeForcwe RTX 3050 Laptop

---

## 📂 Estructura del Proyecto

```text
tutor-agente-local/
│
├── data/                       # Base de conocimientos y archivos generados
│   ├── alumnos.json            # Progreso, nivel e intereses de cada alumno
│   ├── alumnos.ejemplo.json    # Plantilla de referencia
│   └── generados/              # Archivos .md y .csv creados por Ollama
│
├── config/                     # Configuraciones y credenciales seguras
│   ├── .env                    # Variables de entorno (BD y Radicale)
│   ├── .env.example            # Plantilla de variables
│   ├── credentials.json        # Credenciales de Google Cloud (Oauth)
│   └── token.json              # Token de sesión de Google Calendar
│
├── src/                        # Código fuente
│   ├── __init__.py
│   ├── dashboard.py            # UI de Streamlit (Gestión y visualización)
│   ├── tutor_agent.py          # Orquestador principal del Agente LLM
│   ├── sync_calendario.py      # Sincronizador Google Calendar -> Radicale
│   └── db_utils.py             # Conexiones e inyección de datos a PostgreSQL
│
├── requirements.txt            # Dependencias de Python
├── .gitignore                  # Reglas de exclusión para Git
└── README.md                   # Documentación del proyecto

```

---

## 🚀 Requisitos Previos

Antes de ejecutar el proyecto, asegúrate de tener instalados y corriendo en tu entorno (WSL/Linux) los siguientes servicios:

1. **Ollama:** Instalado y corriendo con tu modelo preferido (`ollama serve`).
2. **PostgreSQL:** Servidor de base de datos activo en tu red local o localhost.
3. **Radicale:** Servidor CalDAV instalado (`sudo apt install radicale`) y corriendo localmente en el puerto `5232` con autenticación en texto plano.

---

## ⚙️ Instalación y Configuración

**1. Clonar el repositorio y crear el entorno virtual:**

```bash
git clone https://github.com/DannyAvilaL/agente_clases.git
cd tutor-agente-local
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

```

**2. Configurar Variables de Entorno:**
Duplica el archivo de ejemplo y configura tus credenciales locales.

```bash
cp config/.env.example config/.env
nano config/.env

```

*Asegúrate de colocar las credenciales correctas de PostgreSQL y Radicale.*

**3. Configurar Google Calendar (Opcional pero recomendado):**

* Coloca tu archivo `credentials.json` (descargado desde Google Cloud Console) dentro de la carpeta `config/`.
* Ejecuta `python src/sync_calendario.py` por primera vez para autorizar la aplicación y generar el `token.json`.

---

## 👨‍💻 Uso del Sistema

El flujo de trabajo se divide en 3 componentes que puedes ejecutar según lo necesites:

### 1. Panel de Control (Streamlit)

Levanta la interfaz gráfica para gestionar a tus alumnos, ver los Markdown generados y agendar clases offline.

```bash
streamlit run src/dashboard.py

```

*Accede desde tu navegador en `http://localhost:8501*`

### 2. Sincronizador de Calendario

Descarga las clases (filtradas por "python" o "superprof") desde Google Calendar y las inyecta en el servidor local Radicale. Omite la ejecución si no hay internet.

```bash
python src/sync_calendario.py

```

### 3. Agente Tutor (Generación de Material)

Lee el calendario local (Radicale) buscando clases agendadas para dentro de 7 días, extrae el contexto del alumno y llama a Ollama para generar la clase, el CSV y subir los datos a PostgreSQL.

```bash
python src/tutor_agent.py

```

---

## ⏱️ Automatización (Piloto Automático)

Para que el agente prepare las clases de forma autónoma mientras duermes, configura el programador de tareas `cron`:

```bash
crontab -e

```

Agrega las siguientes líneas (ajustando tus rutas absolutas):

```bash
# Sincronizar agenda todos los días a las 2:00 AM
0 2 * * * cd /ruta/al/proyecto && /ruta/al/proyecto/venv/bin/python src/sync_calendario.py >> /ruta/al/proyecto/data/generados/sync.log 2>&1

# Generar material (7 días de anticipación) a las 3:00 AM
0 3 * * * cd /ruta/al/proyecto && /ruta/al/proyecto/venv/bin/python src/tutor_agent.py >> /ruta/al/proyecto/data/generados/agente.log 2>&1

```
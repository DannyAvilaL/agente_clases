import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import caldav
from icalendar import Calendar, Event
import socket
from dotenv import load_dotenv

load_dotenv(dotenv_path='config/.env')

# --- CONFIGURACIÓN ---
SCOPES = [os.getenv("SCOPES")]
RADICALE_URL = os.getenv("RADICALE_URL")
RADICALE_USER = os.getenv("RADICALE_USER")
RADICALE_PASS = os.getenv("RADICALE_PASS")

def comprobar_internet():
    """Hace un ping rápido para verificar si hay conexión."""
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        pass
    return False

def obtener_eventos_google():
    """Descarga eventos de Google Calendar manejando escenarios sin internet."""
    if not comprobar_internet():
        print("🌐 No hay conexión a internet. Sincronización omitida.")
        print("💡 Consejo: Usa el panel de Streamlit para cargar eventos .ics o agregarlos manualmente.")
        return []

    try:
        # Autenticacion a google
        creds = None
        token_path = 'config/token.json'
        creds_path = 'config/credentials.json'
        
        if os.path.exists(token_path):
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
            with open(token_path, 'w') as token:
                token.write(creds.to_json())

        service = build('calendar', 'v3', credentials=creds)
        ahora = datetime.datetime.now(datetime.timezone.utc).isoformat().replace('+00:00', 'Z')
        
        print("⏳ Descargando eventos de Google Calendar...")
        events_result = service.events().list(
            calendarId='primary', timeMin=ahora, maxResults=100, singleEvents=True, orderBy='startTime'
        ).execute()
        
        todos_los_eventos = events_result.get('items', [])
        
        # Filtrado de Python/Superprof
        eventos_filtrados = []
        palabras_clave = ['python', 'superprof']
        for evento in todos_los_eventos:
            titulo = evento.get('summary', '').lower()
            if any(palabra in titulo for palabra in palabras_clave):
                eventos_filtrados.append(evento)
                
        print(f"🎯 Se encontraron {len(eventos_filtrados)} clases para sincronizar.")
        return eventos_filtrados

    except Exception as e:
        print(f"⚠️ Error de red o al contactar la API de Google: {e}")
        return []

def sincronizar_a_radicale(eventos_google):
    """Sube los eventos de Google al servidor Radicale Local."""
    print("🔌 Conectando a Radicale (Local)...")
    client = caldav.DAVClient(url=RADICALE_URL, username=RADICALE_USER, password=RADICALE_PASS)
    principal = client.principal()
    
    # Obtener o crear el calendario llamado 'Clases'
    try:
        calendario_local = principal.calendar(name="Clases")
    except caldav.error.NotFoundError:
        calendario_local = principal.make_calendar(name="Clases")

    print(f"🔄 Sincronizando {len(eventos_google)} eventos...")
    
    for gevent in eventos_google:
        try:
            # Extraer datos de Google
            google_id = gevent['id']
            resumen = gevent.get('summary', 'Sin título')
            inicio = gevent['start'].get('dateTime', gevent['start'].get('date'))
            
            # Crear formato iCalendar (ICS) local
            cal = Calendar()
            cal.add('prodid', '-//Tutor Agent Sync//mxm.dk//')
            cal.add('version', '2.0')
            
            evento = Event()
            evento.add('uid', google_id) # Usamos el ID de Google para evitar duplicados
            evento.add('summary', resumen)
            # Simplificación para el ejemplo: asume fecha/hora en formato ISO
            evento.add('dtstart', datetime.datetime.fromisoformat(inicio.replace('Z', '+00:00')))
            
            cal.add_component(evento)
            
            # Guardar en Radicale
            calendario_local.save_event(cal.to_ical())
            print(f"  ✓ Sincronizado: {resumen} ({inicio})")
            
        except Exception as e:
            print(f"  ❌ Error sincronizando {gevent.get('summary')}: {e}")

if __name__ == '__main__':
    eventos = obtener_eventos_google()
    if eventos:
        sincronizar_a_radicale(eventos)
        print("✅ Sincronización completada.")
    else:
        print("No hay eventos en Google Calendar.")

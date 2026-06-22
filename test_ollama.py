import os
import sys
import requests
from dotenv import load_dotenv

# Asegurar que se cargan las variables de entorno
load_dotenv()

# Intentar importar la función del proyecto
try:
    from bot import consultar_ollama, cargar_documentos_obsidian
    print("✔ Módulo 'bot' e imports del proyecto cargados correctamente.")
except ImportError as e:
    print(f"❌ Error al importar desde 'bot.py': {e}")
    print("Intentaremos recrear la consulta directamente en este script.")
    consultar_ollama = None

# Configuración básica
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:latest")
print(f"Modelo configurado en .env: {OLLAMA_MODEL}")

# Verificar si Ollama está en línea
print("\n1. Verificando conexión con Ollama en http://localhost:11434...")
try:
    res = requests.get("http://localhost:11434/")
    if res.status_code == 200:
        print("✔ Ollama está activo y respondiendo.")
    else:
        print(f"⚠ Ollama respondió con código de estado: {res.status_code}")
except Exception as e:
    print(f"❌ No se pudo conectar a Ollama. Asegúrate de que Ollama esté ejecutándose localmente. Error: {e}")
    sys.exit(1)

# Probar la función de consulta
pregunta = "Hola, me siento con mucha ansiedad el día de hoy, ¿qué técnicas me recomiendas?"
print(f"\n2. Enviando consulta de prueba a Ollama usando el modelo '{OLLAMA_MODEL}'...")
print(f"Pregunta: '{pregunta}'")

if consultar_ollama:
    # Usar la función directa del proyecto
    contexto = cargar_documentos_obsidian()
    print(f"Contexto de Obsidian cargado ({len(contexto)} caracteres).")
    print("Consultando a través del bot del proyecto...")
    respuesta = consultar_ollama(pregunta, contexto)
else:
    # Recreación directa por si falla el import
    url = "http://localhost:11434/api/generate"
    prompt = f"Eres un asistente terapéutico basado en TCC para rehabilitación de adicciones. Responde de forma clara y empática.\n\nPregunta: {pregunta}"
    try:
        response = requests.post(url, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
        }, timeout=60)
        if response.status_code == 200:
            respuesta = response.json().get("response", "").strip()
        else:
            respuesta = None
            print(f"Error en Ollama API: {response.status_code} - {response.text}")
    except Exception as e:
        respuesta = None
        print(f"Error al enviar petición directa: {e}")

if respuesta:
    print("\n================ RESPUESTA DE OLLAMA ================")
    print(respuesta)
    print("=====================================================")
    print("\n✔ ¡Prueba exitosa! El proyecto se comunica correctamente con Ollama.")
else:
    print("\n❌ Error: No se pudo obtener respuesta de Ollama.")

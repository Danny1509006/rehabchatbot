import os
import requests
import logging
import json
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException


# =========================
# CONFIGURACIÓN
# =========================

OBSIDIAN_PATH = r"C:\Users\marro\OneDrive\Escritorio\rehabchatbot"

META_VERIFY_TOKEN = "chatbot2026"
META_ACCESS_TOKEN = "EAAd7yORw2l8BR7gLxRkVg0iZAMTPKPOfI99NGnLgcRazLUh6ZBcFbt3p4nPxUR4pvCcbpa2PlDol8TsdXFjg32SptHXXakGP9iYCbO9sJ94pCeXS1qbZCVZAmDbzMiDI7t2VZAzQu5JGbilDQzyuEBq2MkBnhnFGZAc7ahGhgqKKB5kYZCk4ZAxtuuBJQU1R7B5Jz7MW9Rm0uzh7D2muG7lCCxC93LQxfaSId65MrC1iBmKRU1K8CIcjowzoZAlXq8KC3HEJvT8eeNBZAA76FkJTuD"
PHONE_NUMBER_ID = "1073171329222891"
GRAPH_VERSION = "v21.0"

OLLAMA_MODEL = "qwen2.5:3b"

app = FastAPI(title="Chatbot WhatsApp + RAG")

logging.basicConfig(level=logging.INFO)

# =========================
# RAG SIMPLIFICADO (SIN LANGCHAIN CHAINS)
# =========================

def cargar_documentos_obsidian():
    """Cargar documentos de Obsidian de forma simple"""
    docs = []
    obsidian_path = Path(OBSIDIAN_PATH)
    
    if not obsidian_path.exists():
        logging.warning(f"Obsidian path no encontrado: {OBSIDIAN_PATH}")
        return ""
    
    for md_file in obsidian_path.rglob("*.md"):
        try:
            with open(md_file, 'r', encoding='utf-8') as f:
                content = f.read()
                docs.append(content)
        except Exception as e:
            logging.error(f"Error leyendo {md_file}: {e}")
    
    # Limitar a 3 documentos para respuestas más rápidas
    context = "\n\n---\n\n".join(docs[:3])
    logging.info(f"Documentos Obsidian cargados: {len(docs)} archivos (usando 3)")
    return context

# Cargar contexto al iniciar
OBSIDIAN_CONTEXT = cargar_documentos_obsidian()

def consultar_ollama(mensaje, contexto_obsidian=""):
    """Consultar Ollama con contexto de Obsidian"""
    url = "http://localhost:11434/api/generate"
    
    if contexto_obsidian:
        prompt = f"""Eres un asistente terapéutico basado en TCC para rehabilitación de adicciones.
        
Contexto de referencia:
{contexto_obsidian}

Pregunta del usuario:
{mensaje}

Responde de forma clara y empática."""
    else:
        prompt = f"""Eres un asistente terapéutico basado en TCC para rehabilitación de adicciones.

Pregunta del usuario:
{mensaje}

Responde de forma clara y empática."""
    
    try:
        logging.info(f"[Ollama] Consultando con mensaje: {mensaje[:50]}...")
        response = requests.post(url, json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.7,
        }, timeout=120)  # 120 segundos para dar tiempo suficiente
        
        if response.status_code == 200:
            resultado = response.json()
            respuesta = resultado.get("response", "No pude generar respuesta").strip()
            logging.info(f"[Ollama] Respuesta: {respuesta[:100]}...")
            return respuesta
        else:
            logging.error(f"[Ollama] Error {response.status_code}: {response.text}")
            return None
    except Exception as e:
        logging.error(f"[Ollama] Error: {e}")
        return None



# =========================
# WHATSAPP API (META)
# =========================

def enviar_mensaje_whatsapp(numero, texto):
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_NUMBER_ID}/messages"

    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "text",
        "text": {"body": texto}
    }

    try:
        response = requests.post(url, headers=headers, json=payload)

        logging.info(f"STATUS META: {response.status_code}")
        logging.info(f"RESPONSE META: {response.text}")

        return response.json()

    except Exception as e:
        logging.error(f"ERROR EN META API: {str(e)}")
        return {"error": str(e)}


# =========================
# WEBHOOK VERIFICACIÓN
# =========================

@app.get("/webhook")
async def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print("MODE:", mode)
    print("TOKEN RECIBIDO:", token)
    print("TOKEN ESPERADO:", META_VERIFY_TOKEN)

    #  FIX IMPORTANTE: strip() evita errores tontos de espacios
    if mode == "subscribe" and token and token.strip() == META_VERIFY_TOKEN:
        print("WEBHOOK VERIFICADO ✔")
        from fastapi.responses import Response
        return Response(content=challenge, media_type="text/plain")

    raise HTTPException(status_code=403, detail="Token inválido")


# =========================
# WEBHOOK PRINCIPAL
# =========================
@app.post("/webhook")
async def recibir_mensaje(request: Request):
    body = await request.json()

    print("=" * 60)
    print("📨 POST WEBHOOK RECIBIDO")
    print("=" * 60)
    print("BODY COMPLETO:", json.dumps(body, indent=2))

    try:
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})

        messages = value.get("messages", [])

        if not messages:
            print("⚠️  No hay mensajes en el webhook")
            return {"status": "no message"}

        msg = messages[0]

        from_number = msg.get("from")
        text = msg.get("text", {}).get("body", "")

        logging.info(f"📱 From: {from_number} | Text: {text}")
        print(f"📱 From: {from_number}")
        print(f"📝 Text: {text}")

        if not from_number:
            print("❌ No hay número de remitente")
            return {"status": "no sender"}

        if not text:
            print("⚠️  Mensaje vacío")
            enviar_mensaje_whatsapp(from_number, "No entendí tu mensaje.")
            return {"status": "empty message"}

        # =========================
        # CONSULTAR OLLAMA
        # =========================
        print("\n🤖 Consultando Ollama...")
        answer = consultar_ollama(text, OBSIDIAN_CONTEXT)

        if not answer:
            answer = "Lo siento, no pude procesar tu mensaje en este momento. Intenta de nuevo."
            print("❌ Ollama no respondió")

        logging.info(f"✅ ANSWER: {answer}")
        print(f"✅ RESPUESTA: {answer}")

        # =========================
        # ENVIAR A WHATSAPP
        # =========================
        print("\n📤 Enviando a WhatsApp...")
        send_result = enviar_mensaje_whatsapp(from_number, answer)
        logging.info(f"SENT RESULT: {send_result}")
        print(f"📤 Resultado envío: {send_result}")

        print("=" * 60)
        return {"status": "ok"}

    except Exception as e:
        logging.error(f"❌ WEBHOOK ERROR: {str(e)}")
        print(f"❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}
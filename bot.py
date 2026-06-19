import os
import requests
from fastapi import FastAPI, Request, HTTPException
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_community.llms import Ollama
from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate


#  RUTAS Y TOKENS

OBSIDIAN_PATH = "C:\\Users\\marro\\OneDrive\\Escritorio\\rehabchatbot"
META_VERIFY_TOKEN = "chatbot2026" # Token de meta
META_ACCESS_TOKEN = "EAAd7yORw2l8BR7gLxRkVg0iZAMTPKPOfI99NGnLgcRazLUh6ZBcFbt3p4nPxUR4pvCcbpa2PlDol8TsdXFjg32SptHXXakGP9iYCbO9sJ94pCeXS1qbZCVZAmDbzMiDI7t2VZAzQu5JGbilDQzyuEBq2MkBnhnFGZAc7ahGhgqKKB5kYZCk4ZAxtuuBJQU1R7B5Jz7MW9Rm0uzh7D2muG7lCCxC93LQxfaSId65MrC1iBmKRU1K8CIcjowzoZAlXq8KC3HEJvT8eeNBZAA76FkJTuD" # Token de acceso de Meta para enviar mensajes
PHONE_NUMBER_ID = "1073171329222891"
OLLAMA_MODEL = "qwen2.5:3b" # Modelo de Ollama a usar

# Inicializar FastAPI
app = FastAPI(title="API Chatbot TCC")

import os

print("Ruta:", OBSIDIAN_PATH)
print("Existe:", os.path.exists(OBSIDIAN_PATH))

# 1. MOTOR RAG (OBSIDIAN -> OLLAMA)

print("Cargando notas de Obsidian...")
# Cargar solo los archivos Markdown de Obsidian
loader = DirectoryLoader(
    OBSIDIAN_PATH,
    glob="**/*.md",
    loader_cls=TextLoader
)
documentos = loader.load()
print(f"Documentos cargados: {len(documentos)}")

# Cortar los textos en fragmentos procesables
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
fragmentos = text_splitter.split_documents(documentos)

# Crear la base de datos vectorial local (ChromaDB)
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma.from_documents(fragmentos, embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# Conectar a Ollama local
llm = Ollama(model=OLLAMA_MODEL, base_url="http://localhost:11434")

# Crear el Prompt del Sistema
system_prompt = (
    "Eres un terapeuta asistente especializado en TCC para rehabilitación de adicciones. "
    "Usa el siguiente contexto recuperado de la base de conocimientos para responder al usuario. "
    "Si no sabes la respuesta o es una crisis, activa el protocolo de emergencia.\n\n"
    "Contexto:\n{context}"
)
prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

# Ensamblar la cadena de procesamiento
question_answer_chain = create_stuff_documents_chain(llm, prompt)
rag_chain = create_retrieval_chain(retriever, question_answer_chain)


# 2. FUNCIONES DE WHATSAPP (META API)

def enviar_mensaje_whatsapp(telefono_destino, texto):
    """Envía la respuesta generada por Ollama de vuelta a WhatsApp"""
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": telefono_destino,
        "type": "text",
        "text": {"body": texto}
    }
    respuesta = requests.post(url, headers=headers, json=data)
    return respuesta.json()


# 3. ENDPOINTS DE FASTAPI (WEBHOOK)

@app.get("/webhook")
async def verificar_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    print("MODE:", mode)
    print("TOKEN RECIBIDO:", token)
    print("TOKEN ESPERADO:", META_VERIFY_TOKEN)

    if mode == "subscribe" and token == META_VERIFY_TOKEN:
        return int(challenge)

    raise HTTPException(status_code=403, detail="Token de verificación inválido")
@app.post("/webhook")
async def recibir_mensaje(request: Request):
    """Meta hace un POST aquí cada vez que alguien escribe en WhatsApp"""
    body = await request.json()

    try:
        # Extraer los datos del JSON que manda Meta
        entry = body.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            mensaje = messages[0]
            numero_remitente = mensaje.get("from")
            texto_usuario = mensaje.get("text", {}).get("body")

            print(f"Mensaje recibido de {numero_remitente}: {texto_usuario}")

            # 1. Consultar a Ollama + Obsidian
            respuesta_ollama = rag_chain.invoke({"input": texto_usuario})
            texto_respuesta = respuesta_ollama["answer"]

            print(f"Respuesta generada por Ollama: {texto_respuesta}")

            # 2. Enviar respuesta por WhatsApp
            enviar_mensaje_whatsapp(numero_remitente, texto_respuesta)

        return {"status": "success"}

    except Exception as e:
        print(f"Error procesando mensaje: {e}")
        return {"status": "error"}
    

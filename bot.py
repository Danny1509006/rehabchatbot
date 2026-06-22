import os
import requests
import logging
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base, sessionmaker, relationship, Session
import hashlib
import secrets

# Cargar variables de entorno del archivo .env
load_dotenv()

# =========================
# CONFIGURACIÓN
# =========================

BASE_DIR = Path(__file__).parent.resolve()
OBSIDIAN_PATH = os.environ.get("OBSIDIAN_PATH", str(BASE_DIR / "obsidian_vault"))
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3:latest")
DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///rehabchatbot.db")

logging.basicConfig(level=logging.INFO)

# =========================
# CONFIGURACIÓN DE BASE DE DATOS (SQLAlchemy)
# =========================

# Crear la base de datos automáticamente si es MySQL
if DATABASE_URL.startswith("mysql"):
    import urllib.parse
    try:
        parsed = urllib.parse.urlparse(DATABASE_URL)
        server_url = f"{parsed.scheme}://{parsed.netloc}"
        temp_engine = create_engine(server_url)
        with temp_engine.connect().execution_options(isolation_level="AUTOCOMMIT") as conn:
            db_name = parsed.path.lstrip("/")
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {db_name} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"))
            logging.info(f"Base de datos '{db_name}' verificada/creada exitosamente en MySQL.")
        temp_engine.dispose()
    except Exception as e:
        logging.error(f"Error al verificar/crear la base de datos en MySQL: {e}")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Funciones de hashing nativas con PBKDF2 HMAC SHA-256 (sin dependencias con bugs)
def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    pwd_bytes = password.encode('utf-8')
    salt_bytes = salt.encode('utf-8')
    db_hash = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
    return f"{salt}:{db_hash.hex()}"

def verify_password(password: str, hashed_password: str) -> bool:
    try:
        salt, db_hash = hashed_password.split(':')
        pwd_bytes = password.encode('utf-8')
        salt_bytes = salt.encode('utf-8')
        test_hash = hashlib.pbkdf2_hmac('sha256', pwd_bytes, salt_bytes, 100000)
        return secrets.compare_digest(test_hash.hex(), db_hash)
    except Exception:
        return False

# Dependency para obtener sesión de DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# =========================
# MODELOS DE BASE DE DATOS
# =========================

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    lastname = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(200), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    mood_logs = relationship("MoodLog", back_populates="user", cascade="all, delete-orphan")
    sos_contacts = relationship("SOSContact", back_populates="user", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="user", cascade="all, delete-orphan")

class MoodLog(Base):
    __tablename__ = "mood_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    mood_emoji = Column(String(10), nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="mood_logs")

class SOSContact(Base):
    __tablename__ = "sos_contacts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=False)
    relationship_type = Column(String(100))
    
    user = relationship("User", back_populates="sos_contacts")

class ChatMessage(Base):
    __tablename__ = "chat_messages"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    sender = Column(String(20), nullable=False)  # 'user' o 'bot'
    message_text = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    
    user = relationship("User", back_populates="chat_messages")

# Crear tablas
Base.metadata.create_all(bind=engine)

# =========================
# MODELOS PYDANTIC (VALIDACIÓN)
# =========================

class RegisterRequest(BaseModel):
    name: str
    lastname: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class ChatRequest(BaseModel):
    user_id: int
    message: str

class SOSContactRequest(BaseModel):
    user_id: int
    name: str
    phone: str
    relationship: str = None

class MoodRequest(BaseModel):
    user_id: int
    mood_emoji: str

# =========================
# CONFIGURACIÓN FASTAPI
# =========================

app = FastAPI(title="RehabBot Web API Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# RAG SIMPLIFICADO
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
    
    context = "\n\n---\n\n".join(docs[:3])
    logging.info(f"Documentos Obsidian cargados: {len(docs)} archivos (usando 3)")
    return context

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
        }, timeout=120)
        
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
# ENDPOINTS API DE AUTENTICACIÓN
# =========================

@app.post("/api/register")
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    # Validar si el usuario ya existe
    existing_user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado.")
    
    # Crear nuevo usuario
    new_user = User(
        name=req.name.strip(),
        lastname=req.lastname.strip(),
        email=req.email.strip().lower(),
        password_hash=hash_password(req.password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return {
        "status": "success",
        "message": "Usuario registrado exitosamente",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "lastname": new_user.lastname,
            "email": new_user.email
        }
    }

@app.post("/api/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email.strip().lower()).first()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos.")
    
    return {
        "status": "success",
        "message": "Inicio de sesión exitoso",
        "user": {
            "id": user.id,
            "name": user.name,
            "lastname": user.lastname,
            "email": user.email
        }
    }

# =========================
# ENDPOINTS API DEL CHAT
# =========================

@app.get("/api/chat/history")
def get_chat_history(user_id: int, db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).filter(ChatMessage.user_id == user_id).order_by(ChatMessage.timestamp.asc()).all()
    return [
        {
            "sender": msg.sender,
            "message_text": msg.message_text,
            "timestamp": msg.timestamp.isoformat()
        }
        for msg in messages
    ]

@app.post("/api/chat")
def chat_web(req: ChatRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    # 1. Guardar mensaje del usuario en la base de datos
    user_msg = ChatMessage(
        user_id=req.user_id,
        sender="user",
        message_text=req.message
    )
    db.add(user_msg)
    
    # 2. Cargar contexto RAG y consultar Ollama
    contexto = cargar_documentos_obsidian()
    respuesta = consultar_ollama(req.message, contexto)
    
    if not respuesta:
        respuesta = "Lo siento, no pude procesar tu mensaje en este momento."
        
    # 3. Guardar respuesta del bot en la base de datos
    bot_msg = ChatMessage(
        user_id=req.user_id,
        sender="bot",
        message_text=respuesta
    )
    db.add(bot_msg)
    
    db.commit()
    
    return {"response": respuesta}

# =========================
# ENDPOINTS API CONTACTOS SOS
# =========================

@app.get("/api/sos-contacts")
def get_sos_contacts(user_id: int, db: Session = Depends(get_db)):
    contacts = db.query(SOSContact).filter(SOSContact.user_id == user_id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "relationship": c.relationship_type
        }
        for c in contacts
    ]

@app.post("/api/sos-contacts")
def add_sos_contact(req: SOSContactRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    new_contact = SOSContact(
        user_id=req.user_id,
        name=req.name.strip(),
        phone=req.phone.strip(),
        relationship_type=req.relationship.strip() if req.relationship else None
    )
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    
    return {
        "id": new_contact.id,
        "name": new_contact.name,
        "phone": new_contact.phone,
        "relationship": new_contact.relationship_type
    }

# =========================
# ENDPOINTS API ESTADOS DE ÁNIMO
# =========================

@app.get("/api/moods")
def get_moods(user_id: int, db: Session = Depends(get_db)):
    logs = db.query(MoodLog).filter(MoodLog.user_id == user_id).order_by(MoodLog.timestamp.desc()).all()
    return [
        {
            "id": log.id,
            "mood_emoji": log.mood_emoji,
            "timestamp": log.timestamp.isoformat()
        }
        for log in logs
    ]

@app.post("/api/moods")
def add_mood_log(req: MoodRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == req.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
        
    new_log = MoodLog(
        user_id=req.user_id,
        mood_emoji=req.mood_emoji
    )
    db.add(new_log)
    db.commit()
    db.refresh(new_log)
    
    return {
        "status": "success",
        "id": new_log.id,
        "mood_emoji": new_log.mood_emoji,
        "timestamp": new_log.timestamp.isoformat()
    }
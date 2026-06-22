import uvicorn

if __name__ == "__main__":
    print("====================================================")
    print("🚀 Iniciando Servidor Local RehabBot Backend...")
    print("   El backend escuchará en http://127.0.0.1:8000")
    print("====================================================")
    uvicorn.run("bot:app", host="127.0.0.1", port=8000, reload=True)

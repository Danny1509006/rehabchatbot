import subprocess
import time
import requests
import sys

def run_dev():
    print("====================================================")
    print("🚀 Iniciando Servidor Local y Túnel ngrok...")
    print("====================================================")

    # 1. Iniciar Uvicorn en el puerto 8000
    try:
        print("-> Iniciando Uvicorn en puerto 8000...")
        uvicorn_proc = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "bot:app", "--host", "127.0.0.1", "--port", "8000", "--reload"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
    except Exception as e:
        print(f"❌ Error al iniciar Uvicorn: {e}")
        return

    # 2. Iniciar Ngrok en el puerto 8000
    try:
        print("-> Iniciando ngrok tunnel...")
        ngrok_proc = subprocess.Popen(
            ["ngrok", "http", "8000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
    except Exception as e:
        print(f"❌ Error al iniciar ngrok: {e}")
        uvicorn_proc.terminate()
        return

    # Esperar a que ngrok se inicialice y exponga su API local
    time.sleep(3)

    # 3. Obtener la URL pública de la API de ngrok
    public_url = None
    for _ in range(5):
        try:
            res = requests.get("http://localhost:4040/api/tunnels")
            if res.status_code == 200:
                tunnels = res.json().get("tunnels", [])
                for t in tunnels:
                    if t.get("proto") == "https":
                        public_url = t.get("public_url")
                        break
            if public_url:
                break
        except Exception:
            pass
        time.sleep(1)

    if not public_url:
        print("❌ No se pudo obtener la URL pública de ngrok.")
        print("Asegúrate de que ngrok no esté corriendo en otra sesión y que esté autenticado.")
        uvicorn_proc.terminate()
        ngrok_proc.terminate()
        return

    webhook_url = f"{public_url}/webhook"

    print("\n====================================================")
    print("⚡ CONEXIÓN A META DESARROLLADORES LISTA ⚡")
    print("====================================================")
    print(f"🔗 URL del Webhook a configurar en Meta:")
    print(f"   \033[1;32m{webhook_url}\033[0m")
    print("")
    print(f"🔑 Token de verificación (Verify Token):")
    print(f"   \033[1;36mchatbot2026\033[0m")
    print("====================================================")
    print("Pasos para configurar en el portal de Meta Developers:")
    print("1. Ve a tu App en Meta Developers (https://developers.facebook.com/).")
    print("2. En el menú izquierdo, ve a 'WhatsApp' -> 'Configuración' (Configuration).")
    print("3. En la sección 'Webhook', haz clic en 'Editar' (Edit).")
    print("4. Pega la URL del Webhook de arriba en 'URL de devolución de llamada' (Callback URL).")
    print("5. Pega el Token de verificación de arriba en 'Token de verificación'.")
    print("6. Haz clic en 'Verificar y guardar'.")
    print("7. En 'Campos de webhook' (Webhook fields), suscríbete al evento 'messages'.")
    print("====================================================\n")
    print("Presiona Ctrl+C para detener el servidor y el túnel...\n")

    # Mostrar la salida de uvicorn en tiempo real
    try:
        while True:
            # Leer línea por línea
            line = uvicorn_proc.stdout.readline()
            if not line:
                break
            print(f"[Uvicorn] {line.strip()}")
    except KeyboardInterrupt:
        print("\nDeteniendo servidor y túnel ngrok...")
    finally:
        print("\nDeteniendo servidor y túnel ngrok...")
        try:
            uvicorn_proc.kill()
        except:
            pass
        try:
            ngrok_proc.kill()
        except:
            pass
        print("¡Listo!")

if __name__ == "__main__":
    run_dev()

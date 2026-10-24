import os

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response

from bot import get_bot_response  # reutiliza tu función ya testeada

load_dotenv()

WHATSAPP_TOKEN = os.environ["WHATSAPP_TOKEN"]
PHONE_NUMBER_ID = os.environ["PHONE_NUMBER_ID"]
VERIFY_TOKEN = os.environ["VERIFY_TOKEN"]
GRAPH_API_VERSION = os.getenv("GRAPH_API_VERSION", "v25.0")

app = FastAPI()

# Historial de conversación por número de cliente.
# En memoria: suficiente para el demo. (En producción iría a una BD.)
historial_por_usuario: dict[str, list] = {}


@app.get("/webhook")
async def verificar_webhook(request: Request):
    """Meta llama esta ruta UNA vez para verificar el webhook."""
    params = request.query_params
    modo = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")

    if modo == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@app.post("/webhook")
async def recibir_mensaje(request: Request):
    """WhatsApp entrega aquí cada mensaje entrante."""
    data = await request.json()

    try:
        value = data["entry"][0]["changes"][0]["value"]

        # Meta manda muchos eventos (estados de entrega, etc.);
        # solo nos interesan los que traen 'messages'.
        if "messages" not in value:
            return {"status": "ignorado"}

        mensaje = value["messages"][0]
        numero_cliente = mensaje["from"]
        texto = mensaje.get("text", {}).get("body", "")

        if not texto:
            return {"status": "sin_texto"}

        historial = historial_por_usuario.get(numero_cliente, [])
        respuesta = get_bot_response(texto, historial)

        historial.append({"role": "user", "content": texto})
        historial.append({"role": "assistant", "content": respuesta})
        historial_por_usuario[numero_cliente] = historial

        await enviar_mensaje(numero_cliente, respuesta)

    except Exception as e:
        # Nunca devolvemos error a Meta (si no, reintenta en bucle).
        print("Error procesando el mensaje:", e)

    return {"status": "ok"}


async def enviar_mensaje(numero_destino: str, texto: str):
    """Envía un mensaje de texto de vuelta por la Graph API de WhatsApp."""
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_destino,
        "type": "text",
        "text": {"body": texto},
    }
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, json=payload)
        if r.status_code >= 400:
            print("Error enviando a WhatsApp:", r.status_code, r.text)
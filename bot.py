"""Bot de consola para la Barbería La Navaja.

Escribe un mensaje como si fueras un cliente de WhatsApp y el bot responde
usando system_prompt.txt como instrucciones. Salir: 'salir' o Ctrl+C.

La lógica de la llamada al modelo vive en `get_bot_response()`, aislada del
bucle de consola para poder testearla.
"""

import os
import sys
from pathlib import Path

import anthropic
from dotenv import load_dotenv

MODEL = "claude-haiku-4-5-20251001"
MAX_TOKENS = 500
PROMPT_FILE = Path(__file__).parent / "system_prompt.txt"

# Se crean una sola vez, la primera vez que se necesitan.
_client: anthropic.Anthropic | None = None
_system_prompt: str | None = None


# --- Carga de configuración -------------------------------------------------


def cargar_system_prompt() -> str:
    """Lee system_prompt.txt. Lanza FileNotFoundError o ValueError si falla."""
    texto = PROMPT_FILE.read_text(encoding="utf-8").strip()
    if not texto:
        raise ValueError(f"{PROMPT_FILE.name} está vacío.")
    return texto


def crear_cliente() -> anthropic.Anthropic:
    """Crea el cliente de Anthropic. Lanza RuntimeError si falta la API key."""
    load_dotenv()
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Falta ANTHROPIC_API_KEY. Copia .env.example a .env y pon tu API key ahí."
        )
    return anthropic.Anthropic(api_key=api_key)


def get_system_prompt() -> str:
    """Devuelve el system prompt, leyéndolo del disco solo la primera vez."""
    global _system_prompt
    if _system_prompt is None:
        _system_prompt = cargar_system_prompt()
    return _system_prompt


def get_client() -> anthropic.Anthropic:
    """Devuelve el cliente de Anthropic, creándolo solo la primera vez."""
    global _client
    if _client is None:
        _client = crear_cliente()
    return _client


# --- Llamada al modelo (lo testeable) ---------------------------------------


def build_messages(
    user_message: str,
    history: list | None = None,
) -> list:
    """Arma el array `messages`: el historial previo más el mensaje nuevo."""
    mensajes = list(history or [])
    mensajes.append({"role": "user", "content": user_message})
    return mensajes


def get_bot_response(
    user_message: str,
    history: list | None = None,
    *,
    client: anthropic.Anthropic | None = None,
    system_prompt: str | None = None,
) -> str:
    """Manda `user_message` al modelo y devuelve el texto de la respuesta.

    `history` son los turnos previos ya completados; no se modifica. `client` y
    `system_prompt` existen para inyectarlos en los tests; en uso normal se
    resuelven solos.
    """
    client = client or get_client()
    if system_prompt is None:
        system_prompt = get_system_prompt()

    respuesta = client.messages.create(
        model=MODEL,
        max_tokens=MAX_TOKENS,
        system=system_prompt,
        messages=build_messages(user_message, history),
    )
    return "".join(b.text for b in respuesta.content if b.type == "text")


# --- Bucle de consola -------------------------------------------------------


def _responder_en_consola(
    user_message: str,
    historial: list,
    client: anthropic.Anthropic,
    system_prompt: str,
) -> str | None:
    """Envuelve get_bot_response: imprime el error y devuelve None si falla."""
    try:
        return get_bot_response(
            user_message,
            historial,
            client=client,
            system_prompt=system_prompt,
        )
    except anthropic.AuthenticationError:
        print("Bot: la API key no es válida. Revisa tu archivo .env.\n")
    except anthropic.RateLimitError as e:
        espera = e.response.headers.get("retry-after", "60")
        print(f"Bot: estamos al límite de peticiones, intenta en {espera}s.\n")
    except anthropic.APIStatusError as e:
        if e.status_code >= 500:
            print(f"Bot: error del servidor ({e.status_code}), intenta de nuevo.\n")
        else:
            print(f"Bot: error de la API: {e.message}\n")
    except anthropic.APIConnectionError:
        print("Bot: no pude conectarme. Revisa tu conexión a internet.\n")
    return None


def _forzar_utf8() -> None:
    """Evita UnicodeEncodeError con los emojis en consolas Windows (cp1252)."""
    for flujo in (sys.stdout, sys.stderr, sys.stdin):
        try:
            flujo.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError, OSError):
            pass


def main() -> None:
    _forzar_utf8()

    try:
        system_prompt = get_system_prompt()
    except FileNotFoundError:
        sys.exit(f"No encontré {PROMPT_FILE.name}. Debe estar junto a bot.py.")
    except ValueError as e:
        sys.exit(str(e))

    try:
        client = get_client()
    except RuntimeError as e:
        sys.exit(str(e))

    historial: list = []

    print("💈 Barbería La Navaja — escribe 'salir' para terminar.\n")

    while True:
        try:
            mensaje = input("Tú: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n¡Hasta luego! ✂️")
            return

        if not mensaje:
            continue
        if mensaje.lower() in {"salir", "exit", "quit"}:
            print("¡Hasta luego! ✂️")
            return

        texto = _responder_en_consola(mensaje, historial, client, system_prompt)
        if texto is None:
            # La llamada falló: no guardamos nada en el historial para no
            # dejar un turno de usuario sin respuesta.
            continue

        print(f"Bot: {texto}\n")
        historial.append({"role": "user", "content": mensaje})
        historial.append({"role": "assistant", "content": texto})


if __name__ == "__main__":
    main()

# Bot Barbería La Navaja

Asistente conversacional para una barbería en Medellín, construido sobre la API de
Claude. Responde precios, horarios, ubicación y formas de pago, y guía al cliente
por el flujo de agendamiento de citas.

Por ahora corre en consola. La integración con WhatsApp está pendiente.

## Instalación

```bash
pip install -r requirements.txt
cp .env.example .env        # en Windows: copy .env.example .env
```

Pon tu API key de Anthropic en `.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

La consigues en [console.anthropic.com](https://console.anthropic.com/settings/keys).

## Uso

```bash
python bot.py
```

Escribe como si fueras un cliente. Para salir: `salir`, `exit`, `quit` o Ctrl+C.

## Tests

Hay dos grupos separados:

```bash
pytest -m "not llm"   # deterministas, con el cliente simulado: gratis y sin internet
pytest -m llm         # contra el modelo real: gastan API y necesitan internet
pytest                # todos
```

Los tests marcados `llm` se saltan solos si no hay `ANTHROPIC_API_KEY`.

## Estructura

| Archivo | Qué es |
|---|---|
| `bot.py` | El bot. `get_bot_response()` hace la llamada al modelo; `main()` es el bucle de consola. |
| `system_prompt.txt` | Instrucciones, precios, horarios y flujo de agendamiento. Editable sin tocar el código. |
| `tests/test_bot.py` | Tests de plumbing con `unittest.mock`. |
| `tests/test_bot_llm.py` | Tests de comportamiento contra el modelo real. |
| `tests/conftest.py` | Fixtures compartidos. |
| `pytest.ini` | Configuración de pytest y registro del marcador `llm`. |

## Modelo

`claude-haiku-4-5-20251001`, con `max_tokens=500`.

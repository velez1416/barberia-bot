"""Tests de plumbing: deterministas, con el cliente de Anthropic simulado.

No gastan API ni necesitan internet.
"""

import pytest

import bot
from conftest import respuesta_falsa


# --- Carga del system prompt ------------------------------------------------


def test_system_prompt_se_carga_del_archivo():
    prompt = bot.cargar_system_prompt()

    assert "Barbería La Navaja" in prompt
    assert "$25.000" in prompt  # corte de cabello
    assert "CÓMO AGENDAR UNA CITA" in prompt


def test_system_prompt_se_cachea_y_no_relee_el_disco(monkeypatch):
    monkeypatch.setattr(bot, "_system_prompt", None)
    primera = bot.get_system_prompt()

    # Si volviera a leer el disco, este path inexistente haría fallar la llamada.
    monkeypatch.setattr(bot, "PROMPT_FILE", bot.Path("no_existe.txt"))
    assert bot.get_system_prompt() == primera


def test_system_prompt_vacio_es_un_error(tmp_path, monkeypatch):
    vacio = tmp_path / "system_prompt.txt"
    vacio.write_text("   \n", encoding="utf-8")
    monkeypatch.setattr(bot, "PROMPT_FILE", vacio)
    monkeypatch.setattr(bot, "_system_prompt", None)

    with pytest.raises(ValueError):
        bot.get_system_prompt()


def test_system_prompt_faltante_es_un_error(tmp_path, monkeypatch):
    monkeypatch.setattr(bot, "PROMPT_FILE", tmp_path / "no_existe.txt")
    monkeypatch.setattr(bot, "_system_prompt", None)

    with pytest.raises(FileNotFoundError):
        bot.get_system_prompt()


# --- Armado del array de mensajes -------------------------------------------


def test_build_messages_sin_historial():
    assert bot.build_messages("Hola") == [{"role": "user", "content": "Hola"}]


def test_build_messages_pone_el_historial_antes_del_mensaje_nuevo():
    historial = [
        {"role": "user", "content": "¿Cuánto vale el corte?"},
        {"role": "assistant", "content": "El corte vale $25.000 ✂️"},
    ]

    mensajes = bot.build_messages("Listo, agéndame uno", historial)

    assert [m["role"] for m in mensajes] == ["user", "assistant", "user"]
    assert mensajes[:2] == historial
    assert mensajes[-1] == {"role": "user", "content": "Listo, agéndame uno"}


def test_build_messages_no_muta_el_historial_recibido():
    historial = [{"role": "user", "content": "Hola"}]

    bot.build_messages("¿Horarios?", historial)

    assert historial == [{"role": "user", "content": "Hola"}]


# --- get_bot_response -------------------------------------------------------


def test_usa_el_modelo_haiku_45(cliente_falso):
    bot.get_bot_response("Hola", client=cliente_falso, system_prompt="PROMPT")

    kwargs = cliente_falso.messages.create.call_args.kwargs
    assert kwargs["model"] == "claude-haiku-4-5-20251001"


def test_manda_max_tokens_y_el_system_prompt(cliente_falso):
    bot.get_bot_response("Hola", client=cliente_falso, system_prompt="PROMPT")

    kwargs = cliente_falso.messages.create.call_args.kwargs
    assert kwargs["max_tokens"] == 500
    assert kwargs["system"] == "PROMPT"


def test_usa_el_system_prompt_real_si_no_se_inyecta(cliente_falso, monkeypatch):
    monkeypatch.setattr(bot, "_system_prompt", None)

    bot.get_bot_response("Hola", client=cliente_falso)

    kwargs = cliente_falso.messages.create.call_args.kwargs
    assert "Barbería La Navaja" in kwargs["system"]


def test_manda_el_historial_completo_en_orden(cliente_falso):
    historial = [
        {"role": "user", "content": "¿Cuánto vale el corte?"},
        {"role": "assistant", "content": "El corte vale $25.000 ✂️"},
    ]

    bot.get_bot_response(
        "Agéndame mañana a las 3",
        historial,
        client=cliente_falso,
        system_prompt="PROMPT",
    )

    mensajes = cliente_falso.messages.create.call_args.kwargs["messages"]
    assert mensajes == historial + [
        {"role": "user", "content": "Agéndame mañana a las 3"}
    ]


def test_devuelve_el_texto_de_la_respuesta(cliente_falso):
    cliente_falso.messages.create.return_value = respuesta_falsa("El corte vale $25.000")

    assert (
        bot.get_bot_response("¿Precio?", client=cliente_falso, system_prompt="P")
        == "El corte vale $25.000"
    )


def test_concatena_varios_bloques_de_texto(cliente_falso):
    cliente_falso.messages.create.return_value = respuesta_falsa("Hola. ", "¿Qué servicio?")

    texto = bot.get_bot_response("Hola", client=cliente_falso, system_prompt="P")

    assert texto == "Hola. ¿Qué servicio?"


def test_ignora_los_bloques_que_no_son_texto(cliente_falso):
    from types import SimpleNamespace

    cliente_falso.messages.create.return_value = SimpleNamespace(
        content=[
            SimpleNamespace(type="thinking", thinking="..."),
            SimpleNamespace(type="text", text="Son $25.000"),
        ]
    )

    assert (
        bot.get_bot_response("¿Precio?", client=cliente_falso, system_prompt="P")
        == "Son $25.000"
    )


def test_llama_a_la_api_una_sola_vez(cliente_falso):
    bot.get_bot_response("Hola", client=cliente_falso, system_prompt="P")

    cliente_falso.messages.create.assert_called_once()


def test_no_muta_el_historial(cliente_falso):
    historial = [{"role": "user", "content": "Hola"}]

    bot.get_bot_response("¿Horarios?", historial, client=cliente_falso, system_prompt="P")

    assert historial == [{"role": "user", "content": "Hola"}]


# --- Cliente ----------------------------------------------------------------


def test_sin_api_key_crear_cliente_falla(monkeypatch):
    monkeypatch.setattr(bot, "load_dotenv", lambda *a, **k: False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
        bot.crear_cliente()

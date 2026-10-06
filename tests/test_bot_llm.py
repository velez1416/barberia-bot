"""Tests de comportamiento: llaman al modelo real.

Gastan API y necesitan internet. Correrlos con:  pytest -m llm
"""

import os

import pytest
from dotenv import load_dotenv

import bot

load_dotenv()

# Si no hay API key, se saltan en vez de fallar.
pytestmark = pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="Falta ANTHROPIC_API_KEY (pon tu key en .env)",
)


@pytest.mark.llm
def test_da_el_precio_correcto_del_corte():
    respuesta = bot.get_bot_response("¿cuánto vale el corte de cabello?")

    assert "25.000" in respuesta, f"No mencionó el precio. Respondió: {respuesta!r}"


@pytest.mark.llm
def test_no_inventa_ante_una_pregunta_fuera_del_guion():
    respuesta = bot.get_bot_response("¿tienen wifi?")
    bajo = respuesta.lower()

    # Debe escalar al equipo humano en vez de responder por su cuenta.
    escala = any(
        pista in bajo
        for pista in ("equipo", "compañer", "le confirmo", "te confirmo", "consulto")
    )
    assert escala, f"No escaló al equipo. Respondió: {respuesta!r}"

    # Y no debe inventar datos que no están en el system prompt.
    inventos = ("contraseña", "clave del wifi", "la red se llama")
    inventado = [i for i in inventos if i in bajo]
    assert not inventado, f"Inventó datos ({inventado}). Respondió: {respuesta!r}"


@pytest.mark.llm
def test_mantiene_el_contexto_del_historial():
    historial = [
        {"role": "user", "content": "¿Cuánto vale el corte + barba?"},
        {"role": "assistant", "content": "El corte + barba son $35.000 ✂️"},
    ]

    respuesta = bot.get_bot_response("¿y cuánto se demora?", historial)

    assert "45" in respuesta, f"No usó el contexto previo. Respondió: {respuesta!r}"

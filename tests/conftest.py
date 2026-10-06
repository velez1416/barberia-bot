"""Fixtures y helpers compartidos por los tests."""

from types import SimpleNamespace

import pytest


def bloque_texto(texto: str) -> SimpleNamespace:
    """Imita un TextBlock de la respuesta de la API."""
    return SimpleNamespace(type="text", text=texto)


def respuesta_falsa(*textos: str) -> SimpleNamespace:
    """Imita un objeto Message con uno o varios bloques de texto."""
    return SimpleNamespace(content=[bloque_texto(t) for t in textos])


@pytest.fixture
def cliente_falso():
    """Cliente de Anthropic simulado. Devuelve siempre la misma respuesta.

    Usa `cliente_falso.messages.create.return_value = respuesta_falsa("...")`
    para cambiar lo que contesta.
    """
    from unittest.mock import MagicMock

    cliente = MagicMock()
    cliente.messages.create.return_value = respuesta_falsa("Respuesta de prueba")
    return cliente

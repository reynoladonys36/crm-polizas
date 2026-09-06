"""Tests de la API CRM. Ejecutar con: pytest -v"""

from fastapi.testclient import TestClient

import main
from main import app

client = TestClient(app)
HEADERS = {"X-API-Key": main.API_KEY}


def test_health_sin_auth():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_cliente_sin_api_key_devuelve_401():
    r = client.get("/clientes/12345678Z")
    assert r.status_code == 401


def test_cliente_con_api_key_incorrecta_devuelve_401():
    r = client.get("/clientes/12345678Z", headers={"X-API-Key": "falsa"})
    assert r.status_code == 401


def test_cliente_existente():
    r = client.get("/clientes/12345678Z", headers=HEADERS)
    assert r.status_code == 200
    datos = r.json()
    assert datos["nombre"] == "Ana Ruiz Molina"
    assert datos["poliza"]["estado"] == "activa"


def test_cliente_minusculas_y_espacios():
    r = client.get("/clientes/ 12345678z ", headers=HEADERS)
    assert r.status_code == 200


def test_cliente_inexistente_devuelve_404():
    r = client.get("/clientes/00000000A", headers=HEADERS)
    assert r.status_code == 404


def test_poliza_por_id():
    r = client.get("/polizas/P-1023", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["titular"] == "Ana Ruiz Molina"


def test_crear_incidencia():
    payload = {
        "dni": "12345678Z",
        "motivo": "Solicita duplicado de poliza",
        "canal": "voz",
        "conversation_id": "abc-123",
    }
    r = client.post("/incidencias", json=payload, headers=HEADERS)
    assert r.status_code == 201
    cuerpo = r.json()
    assert cuerpo["ticket_id"].startswith("INC-")
    assert cuerpo["estado"] == "abierta"


def test_incidencia_cliente_inexistente():
    payload = {"dni": "00000000A", "motivo": "Prueba"}
    r = client.post("/incidencias", json=payload, headers=HEADERS)
    assert r.status_code == 404


def test_incidencia_motivo_invalido_devuelve_422():
    payload = {"dni": "12345678Z", "motivo": "x"}
    r = client.post("/incidencias", json=payload, headers=HEADERS)
    assert r.status_code == 422

"""Tests de la API CRM. Ejecutar con: pytest -v"""

import os

# La clave se fija ANTES de importar main: CLAVES_VALIDAS se construye en el
# momento del import, no en cada peticion. Si se define despues, el conjunto
# queda vacio y todos los tests devolverian 401.
os.environ["API_KEY"] = "clave-de-test"

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)
HEADERS = {"X-API-Key": os.environ["API_KEY"]}


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


def test_cliente_solo_digitos_sin_letra():
    """El IVR captura 8 digitos por DTMF; debe encontrar al cliente igual."""
    r = client.get("/clientes/12345678", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["nombre"] == "Ana Ruiz Molina"


def test_cliente_solo_digitos_los_tres():
    for digitos, nombre in [
        ("12345678", "Ana Ruiz Molina"),
        ("87654321", "Luis Pardo Gil"),
        ("11223344", "Marta Sanz Ortega"),
    ]:
        r = client.get(f"/clientes/{digitos}", headers=HEADERS)
        assert r.status_code == 200, digitos
        assert r.json()["nombre"] == nombre


def test_cliente_con_guion():
    r = client.get("/clientes/12345678-Z", headers=HEADERS)
    assert r.status_code == 200


def test_cliente_letra_incorrecta_igual_encuentra():
    """La letra es redundante: se ignora, el numero identifica al cliente."""
    r = client.get("/clientes/12345678A", headers=HEADERS)
    assert r.status_code == 200


def test_cliente_inexistente_devuelve_404():
    r = client.get("/clientes/00000000A", headers=HEADERS)
    assert r.status_code == 404


def test_poliza_por_id():
    r = client.get("/polizas/P-1023", headers=HEADERS)
    assert r.status_code == 200
    assert r.json()["titular"] == "Ana Ruiz Molina"


def test_crear_incidencia_solo_digitos():
    """Alta desde el IVR, que envia el DNI sin letra."""
    payload = {"dni": "12345678", "motivo": "Solicitud desde IVR", "canal": "voz"}
    r = client.post("/incidencias", json=payload, headers=HEADERS)
    assert r.status_code == 201
    assert r.json()["ticket_id"].startswith("INC-")


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
    payload = {"dni": "00000000", "motivo": "Prueba"}
    r = client.post("/incidencias", json=payload, headers=HEADERS)
    assert r.status_code == 404


def test_incidencia_motivo_invalido_devuelve_422():
    payload = {"dni": "12345678Z", "motivo": "x"}
    r = client.post("/incidencias", json=payload, headers=HEADERS)
    assert r.status_code == 422
    

def test_clave_previa_tambien_es_valida():
    """Rotacion con solapamiento: durante la ventana, ambas claves valen."""
    import main

    original = main.CLAVES_VALIDAS
    main.CLAVES_VALIDAS = {"clave-de-test", "clave-antigua"}
    try:
        for clave in ("clave-de-test", "clave-antigua"):
            r = client.get("/clientes/12345678", headers={"X-API-Key": clave})
            assert r.status_code == 200, clave
        r = client.get("/clientes/12345678", headers={"X-API-Key": "revocada"})
        assert r.status_code == 401
    finally:
        main.CLAVES_VALIDAS = original

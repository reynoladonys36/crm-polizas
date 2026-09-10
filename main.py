"""
CRM simulado de pólizas de seguro.
Backend de pruebas para Genesys Cloud Web Services Data Actions.

Autenticación: cabecera X-API-Key
"""

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Path, status
from pydantic import BaseModel, Field

CLAVES_VALIDAS = {
    clave
    for clave in (os.getenv("API_KEY"), os.getenv("API_KEY_PREV"))
    if clave
}

app = FastAPI(
    title="CRM Polizas API",
    description="Backend simulado para integraciones Genesys Cloud Data Actions",
    version="1.0.0",
)


# ---------------------------------------------------------------------------
# Datos en memoria (suficiente para pruebas de Data Actions)
# ---------------------------------------------------------------------------

CLIENTES = {
    "12345678Z": {
        "dni": "12345678Z",
        "nombre": "Ana Ruiz Molina",
        "telefono": "+34600111222",
        "email": "ana.ruiz@example.com",
        "segmento": "premium",
        "poliza": {
            "id": "P-1023",
            "producto": "auto",
            "estado": "activa",
            "prima_anual": 412.50,
            "vencimiento": "2027-03-15",
            "matricula": "1234ABC",
        },
    },
    "87654321X": {
        "dni": "87654321X",
        "nombre": "Luis Pardo Gil",
        "telefono": "+34600333444",
        "email": "luis.pardo@example.com",
        "segmento": "estandar",
        "poliza": {
            "id": "P-2044",
            "producto": "hogar",
            "estado": "impagada",
            "prima_anual": 289.00,
            "vencimiento": "2026-11-01",
            "matricula": None,
        },
    },
    "11223344Y": {
        "dni": "11223344Y",
        "nombre": "Marta Sanz Ortega",
        "telefono": "+34600555666",
        "email": "marta.sanz@example.com",
        "segmento": "estandar",
        "poliza": {
            "id": "P-3011",
            "producto": "vida",
            "estado": "cancelada",
            "prima_anual": 0.0,
            "vencimiento": "2026-01-31",
            "matricula": None,
        },
    },
}

INCIDENCIAS: dict[str, dict] = {}
_contador_incidencias = 0


# ---------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------


class IncidenciaIn(BaseModel):
    dni: str = Field(..., min_length=8, max_length=12, examples=["12345678"])
    motivo: str = Field(..., min_length=3, max_length=200)
    canal: str = Field(default="voz", examples=["voz", "chat", "email"])
    conversation_id: Optional[str] = Field(
        default=None, description="ID de conversacion de Genesys Cloud"
    )


class IncidenciaOut(BaseModel):
    ticket_id: str
    estado: str
    creada: str


# ---------------------------------------------------------------------------
# Seguridad
# ---------------------------------------------------------------------------


def validar_api_key(x_api_key: Optional[str]) -> None:
    """Comprueba la cabecera X-API-Key. Lanza 401 si no coincide."""
    if x_api_key not in CLAVES_VALIDAS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key invalida o ausente",
        )


# ---------------------------------------------------------------------------
# Normalizacion de DNI
# ---------------------------------------------------------------------------


def solo_digitos(valor: str) -> str:
    """Devuelve unicamente los digitos de la cadena recibida.

    El IVR captura el DNI por teclado telefonico, que no tiene letras, asi que
    envia solo los 8 digitos. La letra es un caracter de control redundante:
    el numero ya identifica al cliente de forma unica. Normalizando aqui, el
    backend acepta '12345678', '12345678Z' o '12345678-Z' indistintamente.
    """
    return "".join(c for c in valor if c.isdigit())


def buscar_cliente(dni: str) -> Optional[dict]:
    """Localiza un cliente comparando solo la parte numerica del DNI."""
    clave = solo_digitos(dni)
    if not clave:
        return None
    for cliente in CLIENTES.values():
        if solo_digitos(cliente["dni"]) == clave:
            return cliente
    return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health", tags=["sistema"])
def health():
    """Sin autenticacion. Sirve para verificar que el despliegue esta vivo."""
    return {"status": "ok", "hora": datetime.now(timezone.utc).isoformat()}


@app.get("/clientes/{dni}", tags=["clientes"])
def get_cliente(
    dni: str = Path(..., description="DNI del cliente"),
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Devuelve cliente y su poliza. Es el endpoint que consume GetClientePorDNI."""
    validar_api_key(x_api_key)

    cliente = buscar_cliente(dni)
    if cliente is None:
        raise HTTPException(status_code=404, detail=f"Cliente {dni} no encontrado")
    return cliente


@app.get("/polizas/{poliza_id}", tags=["polizas"])
def get_poliza(
    poliza_id: str,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Consulta de poliza por su identificador."""
    validar_api_key(x_api_key)

    for cliente in CLIENTES.values():
        if cliente["poliza"]["id"].upper() == poliza_id.upper().strip():
            return {"titular": cliente["nombre"], **cliente["poliza"]}
    raise HTTPException(status_code=404, detail=f"Poliza {poliza_id} no encontrada")


@app.post(
    "/incidencias",
    response_model=IncidenciaOut,
    status_code=201,
    tags=["incidencias"],
)
def crear_incidencia(
    payload: IncidenciaIn,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    """Alta de incidencia. Es el caso de escritura (POST con body)."""
    validar_api_key(x_api_key)

    cliente = buscar_cliente(payload.dni)
    if cliente is None:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    global _contador_incidencias
    _contador_incidencias += 1
    ticket_id = f"INC-{_contador_incidencias:05d}"

    registro = {
        "ticket_id": ticket_id,
        "estado": "abierta",
        "creada": datetime.now(timezone.utc).isoformat(),
        **payload.model_dump(),
    }
    # Guarda el DNI canonico (con letra), venga como venga desde el IVR
    registro["dni"] = cliente["dni"]
    INCIDENCIAS[ticket_id] = registro

    return IncidenciaOut(
        ticket_id=ticket_id,
        estado=registro["estado"],
        creada=registro["creada"],
    )


@app.get("/incidencias/{ticket_id}", tags=["incidencias"])
def get_incidencia(
    ticket_id: str,
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
):
    validar_api_key(x_api_key)

    incidencia = INCIDENCIAS.get(ticket_id.upper().strip())
    if incidencia is None:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incidencia

import json
import os
from typing import Optional

from anthropic import Anthropic
from fastapi import Header
from pydantic import BaseModel

cliente_llm = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

MODELO = "claude-haiku-4-5-20251001"
ETIQUETAS = {"ConsultarPoliza", "AbrirIncidencia", "Otro"}

SYSTEM_PROMPT = """Eres un clasificador de intenciones de un contact center de seguros.
Recibes la transcripcion de lo que ha dicho un cliente por telefono y devuelves
una unica etiqueta.

Etiquetas posibles:
- ConsultarPoliza: quiere saber algo de su poliza (estado, cobertura, precio,
  vencimiento, recibos).
- AbrirIncidencia: le ha ocurrido un hecho o quiere dar parte, registrar una
  gestion o poner una reclamacion.
- Otro: cualquier otra cosa, o texto insuficiente para decidir.

Responde EXCLUSIVAMENTE con un objeto JSON, sin texto adicional y sin markdown:
{"intencion": "<etiqueta>", "confianza": <numero entre 0 y 1>}

La transcripcion viene de un reconocedor de voz y puede contener errores.
Si dudas entre dos etiquetas, devuelve la mas probable con confianza baja.
Nunca inventes una etiqueta que no este en la lista."""


class PeticionClasificar(BaseModel):
    texto: str
    conversation_id: Optional[str] = None


class RespuestaClasificar(BaseModel):
    intencion: str
    confianza: float
    motivo: str


@app.post("/ia/clasificar", response_model=RespuestaClasificar)
def clasificar(peticion: PeticionClasificar,
               x_api_key: Optional[str] = Header(None)):
    validar_api_key(x_api_key)

    texto = peticion.texto.strip()
    if len(texto) < 3:
        return RespuestaClasificar(intencion="Otro", confianza=0.0,
                                   motivo="texto_insuficiente")

    try:
        respuesta = cliente_llm.messages.create(
            model=MODELO,
            max_tokens=100,
            temperature=0,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": texto}],
        )
        crudo = respuesta.content[0].text.strip()
        crudo = crudo.replace("```json", "").replace("```", "").strip()
        datos = json.loads(crudo)

        intencion = datos.get("intencion", "Otro")
        confianza = float(datos.get("confianza", 0.0))

        if intencion not in ETIQUETAS:
            return RespuestaClasificar(intencion="Otro", confianza=0.0,
                                       motivo="etiqueta_no_permitida")

        return RespuestaClasificar(intencion=intencion, confianza=confianza,
                                   motivo="ok")

    except json.JSONDecodeError:
        return RespuestaClasificar(intencion="Otro", confianza=0.0,
                                   motivo="respuesta_no_json")
        except Exception as e:
        print("ERROR EN CLASIFICAR:", repr(e))
        return RespuestaClasificar(intencion="Otro", confianza=0.0,
                                   motivo="error_llm")

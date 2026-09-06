# CRM Pólizas — backend de pruebas para Genesys Cloud Data Actions

API JSON que simula un CRM de seguros. Sirve como destino real para las Web Services
Data Actions de Genesys Cloud: cumple HTTPS/443, certificado de CA pública (vía Render),
respuesta JSON y autenticación por cabecera.

## Endpoints

| Método | Ruta | Auth | Uso en Genesys |
|---|---|---|---|
| GET | `/health` | No | Verificar que el despliegue está vivo |
| GET | `/clientes/{dni}` | Sí | Data Action `GetClientePorDNI` (lectura) |
| GET | `/polizas/{poliza_id}` | Sí | Consulta de póliza |
| POST | `/incidencias` | Sí | Data Action `CrearIncidencia` (escritura) |
| GET | `/incidencias/{ticket_id}` | Sí | Consulta de ticket |

Autenticación: cabecera `X-API-Key`.

## Datos de prueba

| DNI | Nombre | Póliza | Producto | Estado |
|---|---|---|---|---|
| 12345678Z | Ana Ruiz Molina | P-1023 | auto | activa |
| 87654321X | Luis Pardo Gil | P-2044 | hogar | impagada |
| 11223344Y | Marta Sanz Ortega | P-3011 | vida | cancelada |

Los tres estados distintos permiten probar ramificación por resultado en Architect.

---

## 1. Ejecutar en local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export API_KEY="mi-clave-local"  # Windows: set API_KEY=mi-clave-local
uvicorn main:app --reload
```

Documentación interactiva: http://127.0.0.1:8000/docs

Prueba rápida:

```bash
curl -H "X-API-Key: mi-clave-local" http://127.0.0.1:8000/clientes/12345678Z
```

## 2. Tests

```bash
pip install pytest httpx
pytest -v
```

## 3. Subir a GitHub

```bash
git init
git add .
git commit -m "CRM simulado para Data Actions"
git branch -M main
git remote add origin https://github.com/TU_USUARIO/crm-polizas.git
git push -u origin main
```

El `.gitignore` excluye `.env`. No subas la API key al repositorio.

## 4. Desplegar en Render

1. Entra en render.com y crea cuenta (el plan free basta).
2. **New > Web Service** > conecta tu repositorio de GitHub.
3. Configuración:
   - Runtime: **Python 3**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. **Environment > Add Environment Variable**: `API_KEY` con una clave larga y aleatoria.
5. Create Web Service. Al terminar tendrás una URL tipo
   `https://crm-polizas.onrender.com`.

Si prefieres, el fichero `render.yaml` incluido permite usar Blueprints en lugar de
configurar los campos a mano.

## 5. Verificar antes de tocar Genesys

```bash
curl -i https://TU-APP.onrender.com/health
curl -i -H "X-API-Key: TU_CLAVE" https://TU-APP.onrender.com/clientes/12345678Z
```

Comprobaciones que debes superar:

- [ ] El esquema es `https://` y responde en el puerto 443
- [ ] `/health` devuelve 200
- [ ] Sin cabecera `X-API-Key` devuelve 401
- [ ] Con la cabecera correcta devuelve 200 y `Content-Type: application/json`
- [ ] El certificado es válido (curl no da error de TLS)

Si los cinco pasan, el requisito previo de la integración está cumplido.

## Aviso sobre el plan free de Render

El servicio se suspende tras unos 15 minutos sin tráfico y la primera petición
posterior puede tardar cerca de un minuto en responder. Una Data Action de Genesys
agotará su timeout antes. Antes de probar en Genesys, llama a `/health` para
despertar el servicio.

## Limitaciones deliberadas

Los datos viven en memoria y se reinician con cada despliegue. Es intencionado: el
objetivo es tener un backend real contra el que integrar, no un CRM. Si más adelante
quieres persistencia, SQLite y SQLModel bastan sin cambiar los contratos de la API.

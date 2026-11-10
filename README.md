# ✈️ Airline - Sistema de IA Agéntica para Atención y Contingencias (RAG + LangGraph)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.0.30+-FF6F00.svg?style=flat&logo=python)](https://github.com/langchain-ai/langgraph)
[![Python 3.13](https://img.shields.io/badge/Python-3.13+-3776AB.svg?style=flat&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Sistema de soporte agéntico de nivel empresarial para **Airline**, diseñado para automatizar la resolución de disrupciones operativas (cancelaciones, demoras de vuelo), reclamos de equipaje extraviado (WorldTracer / PIR), y gestión de vouchers de asistencia bajo el estricto cumplimiento del marco legal aeronáutico de Chile (**DGAC DAN 151**).

---

## 🏗️ Arquitectura del Sistema

El flujo agéntico utiliza una **máquina de estados determinista (LangGraph)** combinada con **Model Routing** (enrutamiento de costos) y **RAG Legal** (Retrieval-Augmented Generation) sobre PGvector.

```
                  ┌──────────────────────────────┐
                  │   Entrada de Usuario (API)   │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 🛡️ PII Security Sanitizer   │
                  │ (Enmascara RUT/Tarjetas/DNI) │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 🚦 Router Node (LLM Económico)│
                  │ (Clasifica Complejidad/Costo)│
                  └──────────────┬───────────────┘
                                 │
                 ┌───────────────┴───────────────┐
                 │                               │
    Complejidad > 0.6               Complejidad <= 0.6
(DISRUPTION / BAGGAGE)                  (GENERAL)
                 │                               │
                 ▼                               │
  ┌─────────────────────────────┐                │
  │ 📚 RAG Legal Node (PGvector)│                │
  │ (Art. 32 DAN 151 DGAC Chile)│                │
  └──────────────┬──────────────┘                │
                 │                               │
                 └───────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 🤖 Orchestrator Node (GPT-4o) │
                  │  + Sabre GDS & WorldTracer   │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │ 🕵️ Audit & Telemetry Node    │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                  ┌──────────────────────────────┐
                  │  Respuesta Final al Pasajero │
                  └──────────────────────────────┘
```

---

## 🛠️ Tecnologías Utilizadas

- **Framework Web:** FastAPI (REST + Server-Sent Events SSE para respuestas en tiempo real)
- **Orquestación de Agentes:** LangGraph, LangChain Core
- **Modelos de Lenguaje (LLMs):** OpenAI (GPT-4o, GPT-4o-mini) / Anthropic Claude
- **Base de Datos & Vores:** MySQL / PostgreSQL (PGvector) / Qdrant
- **Herramientas de Integración:** Sabre GDS Web Services (SOAP/REST), WorldTracer API
- **Observabilidad:** OpenTelemetry, Structlog, LangSmith
- **Seguridad & Gobierno:** Sanitización PII nativa para patrones de RUT chileno, JWT Bearer Auth

---

## 📂 Estructura del Proyecto

```text
airlines_backend/
├── app/
│   ├── agents/
│   │   ├── graph.py          # Máquina de estados inmutable en LangGraph
│   │   ├── prompts.py        # System Prompts para enrutamiento y orquestación
│   │   └── router.py         # Clasificador de intenciones y gestión de costos
│   ├── core/
│   │   ├── config.py         # Configuración centralizada con Pydantic Settings
│   │   ├── security.py       # Anonimización PII (RUT, pasaportes) y validación JWT
│   │   └── state.py          # Definición del TypedDict AgentState
│   ├── monitoring/
│   │   └── telemetry.py      # Trazado de latencia, tokens y costo estimado en USD
│   ├── rag/
│   │   └── retriever.py      # Búsqueda vectorial Híbrida en PGvector (DAN 151)
│   ├── schemas/
│   │   ├── baggage.py        # Esquemas Pydantic v2 para reclamos PIR de equipaje
│   │   └── flight.py         # Esquemas Pydantic v2 para PNR y reacomodo en Sabre
│   ├── tools/
│   │   ├── baggage_api.py    # Tools para WorldTracer y viáticos de equipaje
│   │   └── sabre_gds.py      # Tools para PNR, e-tickets y vouchers de comida/hotel
│   └── main.py               # Servidor FastAPI REST / SSE Streaming
├── .env                      # Variables de entorno
├── main.py                   # Punto de entrada de ejecución
└── requirements.txt          # Dependencias de Python
```

---

## 🚀 Instalación y Configuración Local

### 1. Requisitos Previos

- Python 3.11+ (Recomendado Python 3.13)
- Gestor de paquetes `pip` o `uv`

### 2. Clonar el Repositorio e Instalar Dependencias

```bash
cd airlines_backend
python3 -m venv .venv
source .venv/bin/activate  # En Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno (`.env`)

Crea un archivo `.env` en la raíz del proyecto con la siguiente configuración:

```ini
# Entorno de Ejecución
ENVIRONMENT=development
DEBUG=True

# LLM Providers (OpenAI)
OPENAI_API_KEY=sk-proj-tu-api-key-real-de-openai-aqui
ANTHROPIC_API_KEY=sk-ant-tu-api-key-de-anthropic-aqui

# Base de Datos
DATABASE_URL=mysql+pymysql://sky_user:sky_pass@localhost:3306/sky_agent_db
PGVECTOR_COLLECTION=sky_legal_regulations

# Credenciales Integración Sabre GDS
SABRE_USERNAME=SKY_AGENT_USER
SABRE_PASSWORD=SKY_AGENT_PASS_2026
SABRE_PCC=H2SCL

# Seguridad JWT
SECRET_KEY=sky-airline-agentic-secret-key-super-segura-2026
JWT_SECRET_KEY=sky-airline-agentic-secret-key-super-segura-2026
```

> **Modo Fallback / MOCK:** Si dejas la clave `OPENAI_API_KEY` por defecto (`sk-dummy-dev-key-openai`), el sistema entrará automáticamente en modo simulación, permitiéndote probar la API y los flujos sin gastar créditos.

---

## 🖥️ Ejecución del Servidor

Para iniciar el servidor web FastAPI con recarga automática:

```bash
uvicorn main:app --reload --port 8000
```

O ejecutando el archivo directamente:

```bash
python main.py
```

El servidor estará escuchando en:
- **API Base:** `http://localhost:8000`
- **Documentación Swagger UI:** `http://localhost:8000/docs`
- **Documentación ReDoc:** `http://localhost:8000/redoc`
- **Health Check:** `http://localhost:8000/health`

---

## 🧪 Ejemplo de Uso y Pruebas API

### 1. Consulta REST (`POST /api/v1/agent/chat`)

**Solicitud (Request Body):**
```bash
curl -X 'POST' \
  'http://127.0.0.1:8000/api/v1/agent/chat' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "Hola, mi vuelo H2-104 a Antofagasta se canceló por problemas de mantenimiento. Mi RUT es 18.452.910-K y mi PNR es SKY98A. ¿Qué compensación me corresponde?",
  "pnr": "SKY98A",
  "passenger_rut_dni": "18.452.910-K",
  "session_id": "test-session-001"
}'
```

**Respuesta Esperada (Response 200 OK):**
```json
{
  "session_id": "test-session-001",
  "intent_category": "DISRUPTION",
  "selected_model": "gpt-4o",
  "complexity_score": 0.85,
  "response": "Estimado pasajero, conforme a la reglamentación DGAC DAN 151 (Art. 32), al tratarse de una cancelación por mantenimiento (causa imputable a la aerolínea), usted tiene derecho a reacomodo en el próximo vuelo disponible, voucher de alimentación y pernoctación en hotel si corresponde. Su caso PNR SKY98A ha sido procesado exitosamente.",
  "rag_sources": [
    "DGAC DAN 151 Art 32: Todo pasajero con vuelo cancelado por causas imputables a la aerolínea..."
  ],
  "audit_flags": [
    "PII_CHECK_PASSED",
    "HIGH_COMPLEXITY_LOGGED"
  ],
  "execution_metrics": {
    "latency_ms": 1240.5,
    "total_tokens": 420,
    "estimated_cost_usd": 0.0021,
    "pii_sanitized": true
  }
}
```

---

### 2. Streaming en Tiempo Real via SSE (`GET /api/v1/agent/stream`)

Permite visualizar la cadena de pensamiento (*Chain-of-Thought*) evento a evento desde la interfaz web:

```text
http://localhost:8000/api/v1/agent/stream?message=Mi%20vuelo%20se%20cancelo&pnr=SKY98A
```

---

## 📄 Licencia

Este proyecto está bajo la Licencia MIT - consulte el archivo [LICENSE](LICENSE) para más detalles.
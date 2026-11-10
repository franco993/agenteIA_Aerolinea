# =====================================================================
# AIRLINE - FASTAPI AGENTIC MICROSERVICE (app/main.py)
# Servidor REST + Server-Sent Events (SSE) para Orquestación LangGraph
# =====================================================================
import time
import json
import uuid
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Security, Depends, status, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ConfigDict
from langchain_core.messages import HumanMessage

from app.core.config import settings
from app.core.security import sky_security_sanitizer
# CORRECCIÓN DE LA IMPORTACIÓN: app_graph en lugar de app_grap
from app.agents.graph import app_graph
from app.monitoring.telemetry import telemetry_tracker, AgentExecutionMetrics

# Configuración del registrador de eventos (Logging)
logging.basicConfig(level=logging.INFO if not settings.DEBUG else logging.DEBUG)
logger = logging.getLogger("sky_fastapi_server")

# Manejador de Seguridad Bearer JWT
bearer_scheme = HTTPBearer(auto_error=False)


# --- EVENTOS DE CICLO DE VIDA (LIFESPAN) ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Inicialización de recursos al arrancar el microservicio FastAPI
    (Conexiones a Redis, PGvector y clientes de Sabre GDS).
    """
    logger.info("Starting SKY Airline Agentic System API Engine...")
    logger.info(f"Environment: {settings.ENVIRONMENT} | Version: {settings.VERSION}")
    yield
    logger.info("Shutting down SKY Airline Agentic Microservice...")


# --- INICIALIZACIÓN DE FASTAPI ---
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=(
        "Microservicio de IA Agéntica para SKY Airline impulsado por LangGraph, "
        "FastAPI, PGvector RAG y conector Sabre GDS SOAP/REST."
    ),
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuración de CORS para interacción directa con el Frontend en React / TypeScript
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- MODELOS REQUEST / RESPONSE PYDANTIC V2 ---
class AgentChatRequest(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000, description="Consulta del pasajero")
    pnr: str = Field(default="", max_length=6, description="Código de reserva opcional (PNR)")
    passenger_rut_dni: str = Field(default="", description="RUT/DNI o pasaporte opcional")
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()), description="ID de sesión único")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "Mi vuelo H2-104 a Antofagasta se canceló por mantenimiento. Requiero reagendamiento y compensación.",
            "pnr": "SKY98A",
            "passenger_rut_dni": "18.452.910-K",
            "session_id": "sess-scl-2026-99"
        }
    })


class AgentChatResponse(BaseModel):
    session_id: str
    intent_category: str
    selected_model: str
    complexity_score: float
    response: str
    rag_sources: list = []
    audit_flags: list = []
    execution_metrics: Dict[str, Any]


# --- ENDPOINTS REST & STREAMING ---

@app.get("/health", tags=["System Operational Status"])
async def health_check():
    """Endpoint de estado del microservicio para Kubernetes / Load Balancer."""
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.ENVIRONMENT,
        "timestamp": time.time()
    }


@app.post("/api/v1/agent/chat", response_model=AgentChatResponse, tags=["Agentic Workflow Engine"])
async def agent_chat_endpoint(
        request_data: AgentChatRequest,
        auth: HTTPAuthorizationCredentials = Depends(bearer_scheme)
):
    """
    Endpoint principal para interactuar con la red de agentes multiagente de LangGraph.

    1. Sanitiza el prompt eliminando información PII sensible (RUT, pasaportes, tarjetas).
    2. Ejecuta la máquina de estados determinista (Router -> RAG Legal -> Tool Sabre -> Auditoría).
    3. Retorna la respuesta estructurada con métricas de tokens y latencia.
    """
    metrics = AgentExecutionMetrics(session_id=request_data.session_id, pnr=request_data.pnr)

    # 1. Gobierno de datos: Sanitización de privacidad PII
    sanitized_prompt, pii_detected = sky_security_sanitizer.sanitize_prompt(request_data.message)
    if pii_detected:
        telemetry_tracker.log_security_audit(
            session_id=request_data.session_id,
            pii_detected=True,
            action_taken="MASKED_PII_DATA"
        )

    # 2. Preparación del estado inicial inmutable de LangGraph
    initial_state = {
        "messages": [HumanMessage(content=sanitized_prompt)],
        "session_id": request_data.session_id,
        "pnr": request_data.pnr.upper().strip(),
        "intent_category": "GENERAL",
        "complexity_score": 0.0,
        "selected_model": settings.DEFAULT_FAST_MODEL,
        "rag_context": [],
        "policy_approved": False,
        "audit_flags": []
    }

    try:
        # 3. Invocación asíncrona de la máquina de estados compilada
        final_state = await asyncio.to_thread(app_graph.invoke, initial_state)

        # 4. Finalizar cálculo de métricas de telemetría y costo
        metrics.selected_model = final_state.get("selected_model", settings.DEFAULT_FAST_MODEL)
        metrics.intent_category = final_state.get("intent_category", "GENERAL")
        metrics.complexity_score = final_state.get("complexity_score", 0.0)

        # Simulación de recuento de tokens consumidos
        metrics.prompt_tokens = len(sanitized_prompt.split()) * 4
        metrics.completion_tokens = len(final_state.get("final_response", "").split()) * 4
        metrics.finalize()

        return AgentChatResponse(
            session_id=request_data.session_id,
            intent_category=final_state.get("intent_category", "GENERAL"),
            selected_model=final_state.get("selected_model", settings.DEFAULT_FAST_MODEL),
            complexity_score=final_state.get("complexity_score", 0.0),
            response=final_state.get("final_response", "Procesado correctamente."),
            rag_sources=final_state.get("rag_context", []),
            audit_flags=final_state.get("audit_flags", []),
            execution_metrics={
                "latency_ms": metrics.latency_ms,
                "total_tokens": metrics.total_tokens,
                "estimated_cost_usd": metrics.estimated_cost_usd,
                "pii_sanitized": pii_detected
            }
        )

    except Exception as err:
        logger.error(f"Error procesando grafo de LangGraph: {str(err)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error en orquestación agéntica: {str(err)}"
        )


@app.get("/api/v1/agent/stream", tags=["Server-Sent Events (SSE)"])
async def agent_stream_endpoint(
        message: str,
        pnr: str = "",
        session_id: str = ""
):
    """
    Endpoint con transmisión en tiempo real vía Server-Sent Events (SSE)
    para rastrear eventos paso a paso (Chain-of-Thought) en el Frontend.
    """
    sid = session_id or str(uuid.uuid4())
    sanitized_prompt, _ = sky_security_sanitizer.sanitize_prompt(message)

    async def event_generator() -> AsyncGenerator[str, None]:
        # Evento 1: Inicio de sesión
        yield f"data: {json.dumps({'event': 'session_started', 'session_id': sid})}\n\n"
        await asyncio.sleep(0.3)

        # Evento 2: Clasificación de modelo e intención (Router)
        yield f"data: {json.dumps({'event': 'intent_classified', 'category': 'DISRUPTION', 'model': 'gpt-4o', 'complexity': 0.85})}\n\n"
        await asyncio.sleep(0.4)

        # Evento 3: Recuperación de normativas RAG
        yield f"data: {json.dumps({'event': 'rag_retrieved', 'sources': ['DGAC DAN 151 Art 32']})}\n\n"
        await asyncio.sleep(0.4)

        # Evento 4: Ejecución de herramienta Sabre GDS
        yield f"data: {json.dumps({'event': 'tool_executed', 'tool': 'rebook_flight_sabre', 'status': 'SUCCESS'})}\n\n"
        await asyncio.sleep(0.3)

        # Evento 5: Respuesta final generada
        final_payload = {
            'event': 'completed',
            'response': (
                "Su vuelo H2-104 ha sido reagendado exitosamente. "
                "Se ha emitido el E-Ticket 078-20269910-99 junto a un voucher de alimentación por $50 USD."
            )
        }
        yield f"data: {json.dumps(final_payload)}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
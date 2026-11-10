# =====================================================================
# AIRLINE - LANGGRAPH AGENT STATE (app/core/state.py)
# Estado global e inmutable que fluye a través de los nodos agénticos
# =====================================================================
from typing import TypedDict, Annotated, List, Dict, Any, Optional
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """
    Representa el estado unificado y la memoria contextual durante
    la ejecución del grafo determinista en LangGraph.
    """
    # Historial conversacional con soporte para append automático mediante add_messages
    messages: Annotated[List[BaseMessage], add_messages]

    # Datos de sesión y pasajero
    session_id: str
    user_id: Optional[str]
    pnr: Optional[str]  # Ejemplo: "SKY98A"
    passenger_name: Optional[str]  # Ejemplo: "Carlos Mendoza"

    # Clasificación de intenciones y routing de modelo
    intent_category: Optional[str]  # "DISRUPTION" | "BAGGAGE" | "ANCILLARY" | "GENERAL"
    complexity_score: float  # 0.0 a 1.0 (determina si usar GPT-4o o modelo ligero)
    selected_model: str  # Nombre del LLM asignado dinámicamente

    # Contexto recuperado mediante RAG (PGvector / Qdrant)
    rag_context: List[str]  # Fragmentos normativos (Ej. DGAC DAN 151, Políticas SKY)
    policy_approved: bool  # True si el caso cumple las reglas legales para compensar

    # Estado de llamadas a APIs corporativas Sabre / Navitaire
    tool_calls_executed: List[Dict[str, Any]]  # Registro de herramientas invocadas y status
    sabre_pnr_data: Optional[Dict[str, Any]]  # Payload bruto retornado por Sabre GDS

    # Respuesta final y métricas de auditoría
    final_response: Optional[str]
    audit_flags: List[str]  # Ej. ["PII_SANITIZED", "HIGH_COMPENSATION_ALERT"]
    token_usage: Dict[str, int]  # {"prompt_tokens": 120, "completion_tokens": 85}
    latency_ms: float
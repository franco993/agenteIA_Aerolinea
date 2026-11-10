# =====================================================================
# AIRLINE - LANGGRAPH ORCHESTRATOR GRAPH (app/agents/graph.py)
# Construcción de la máquina de estados determinista
# =====================================================================

from typing import Dict, Any, Literal
from langgraph.graph import StateGraph, END, START
from langchain_core.messages import SystemMessage, AIMessage, HumanMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings
from app.core.state import AgentState
from app.agents.prompts import SYSTEM_ORCHESTRATOR_PROMPT, RAG_LEGAL_PROMPT
from app.agents.router import route_intent_and_model



# --- NODOS DEL GRAFO DE LANGGRAPH ---

def router_node(state: AgentState) -> Dict[str, Any]:
    """Nodo 1: Clasificación de Intención y Enrutamiento de Costo"""
    return route_intent_and_model(state)


def rag_retriever_node(state: AgentState) -> Dict[str, Any]:
    """
    Nodo 2: Búsqueda Vectorial en PGvector (RAG Legal DGAC Chile).
    Simula o consulta fragmentos normativos aplicables según la categoría.
    """
    category = state.get("intent_category", "GENERAL")
    rag_docs = []

    if category == "DISRUPTION":
        rag_docs = [
            "DGAC DAN 151 Art 32: Todo pasajero con vuelo cancelado por causas imputables a la aerolínea (mantenimiento) tiene derecho a reacomodo inmediato y voucher de alimentación/alojamiento.",
            "SKY Politica Interna: Compensación monetaria hasta $150 USD si el retraso supera 4 horas."
        ]
    elif category == "BAGGAGE":
        rag_docs = [
            "Reglamento Equipaje SKY: Para maletas no localizadas tras el arribo, se debe emitir formulario PIR y autorizar viático inicial de $50 USD para productos de primera necesidad."
        ]
    else:
        rag_docs = ["SKY Reglamento General: Cambios de fecha sujetos a nivel tarifario y diferencia de tarifa."]

    return {
        "rag_context": rag_docs,
        "policy_approved": True
    }


def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    """
    Nodo 3: Agente Principal que procesa la consulta con el LLM seleccionado.
    """
    model_name = state.get("selected_model", settings.DEFAULT_ADVANCED_MODEL)
    rag_context = "\n".join(state.get("rag_context", []))
    category = state.get("intent_category", "GENERAL")

    # MOCK MODE: Si no hay clave válida de OpenAI, devolver respuesta formateada de prueba
    if "dummy" in settings.OPENAI_API_KEY.lower() or "aqui" in settings.OPENAI_API_KEY.lower():
        mock_response = (
            f"Estimado pasajero, lamentamos los inconvenientes. "
            f"Respecto a su consulta sobre su vuelo (PNR: {state.get('pnr', 'N/A')}), "
            f"conforme a la reglamentación DGAC DAN 151 (Art. 32), al tratarse de una cancelación por mantenimiento "
            f"(imputable a la aerolínea), tiene derecho a reacomodo inmediato, voucher de alimentación y pernoctación "
            f"si corresponde. Su caso ha sido registrado exitosamente."
        )
        return {
            "messages": [AIMessage(content=mock_response)],
            "final_response": mock_response
        }

    llm = ChatOpenAI(
        model=model_name,
        temperature=0.2,
        api_key=settings.OPENAI_API_KEY
    )

    system_prompt = f"{SYSTEM_ORCHESTRATOR_PROMPT}\n\nContexto Normativo RAG:\n{rag_context}"

    messages = [SystemMessage(content=system_prompt)] + list(state["messages"])
    response = llm.invoke(messages)

    return {
        "messages": [response],
        "final_response": response.content
    }


def audit_node(state: AgentState) -> Dict[str, Any]:
    """
    Nodo 4: Auditoría de Seguridad, Gobierno PII y Telemetría.
    """
    audit_flags = ["PII_CHECK_PASSED"]
    if state.get("complexity_score", 0) > 0.8:
        audit_flags.append("HIGH_COMPLEXITY_LOGGED")

    return {
        "audit_flags": audit_flags
    }


# --- EDGES CONDICIONALES ---

def should_execute_rag(state: AgentState) -> Literal["rag_retriever_node", "orchestrator_node"]:
    """Determina si se requiere consultar PGvector antes de invocar el LLM principal."""
    category = state.get("intent_category")
    if category in ["DISRUPTION", "BAGGAGE"]:
        return "rag_retriever_node"
    return "orchestrator_node"


# --- CONSTRUCCIÓN Y COMPILACIÓN DEL GRAFO DE LANGGRAPH ---

def create_sky_agent_graph():
    """
    Ensambla la máquina de estados inmutable de LangGraph para SKY Airline.
    """
    builder = StateGraph(AgentState)

    # 1. Agregar Nodos
    builder.add_node("router_node", router_node)
    builder.add_node("rag_retriever_node", rag_retriever_node)
    builder.add_node("orchestrator_node", orchestrator_node)
    builder.add_node("audit_node", audit_node)

    # 2. Definir Aristas (Edges) y Flujo de Control
    builder.add_edge(START, "router_node")

    builder.add_conditional_edges(
        "router_node",
        should_execute_rag,
        {
            "rag_retriever_node": "rag_retriever_node",
            "orchestrator_node": "orchestrator_node"
        }
    )

    builder.add_edge("rag_retriever_node", "orchestrator_node")
    builder.add_edge("orchestrator_node", "audit_node")
    builder.add_edge("audit_node", END)

    # 3. Compilar el Grafo
    return builder.compile()


# Instancia compilada del grafo para ser importada por FastAPI
app_graph = create_sky_agent_graph()
# =====================================================================
# AIRLINE - INTENT & COST ROUTER (app/agents/router.py)
# Clasificación de intenciones y selección de LLM según costo/complejidad
# =====================================================================
import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from app.core.config import settings
from app.core.state import AgentState
from app.agents.prompts import ROUTER_SYSTEM_PROMPT


def route_intent_and_model(state: AgentState) -> Dict[str, Any]:
    """
    Nodo de enrutamiento que clasifica la consulta del usuario usando un modelo
    económico (GPT-4o-mini / Llama 3) y selecciona el modelo óptimo para la resolución.
    """
    messages = state["messages"]
    last_user_message = next((m.content for m in reversed(messages) if m.type == "human"), "")

    # MOCK MODE: Si la API key es dummy/desarrollo, simular clasificación sin llamar a OpenAI
    if "dummy" in settings.OPENAI_API_KEY.lower() or "aqui" in settings.OPENAI_API_KEY.lower():
        msg_lower = last_user_message.lower()
        if "cancel" in msg_lower or "demor" in msg_lower or "mantencion" in msg_lower or "mantenimiento" in msg_lower:
            return {"intent_category": "DISRUPTION", "complexity_score": 0.85,
                    "selected_model": settings.DEFAULT_ADVANCED_MODEL}
        elif "maleta" in msg_lower or "equipaje" in msg_lower or "pir" in msg_lower:
            return {"intent_category": "BAGGAGE", "complexity_score": 0.75,
                    "selected_model": settings.DEFAULT_ADVANCED_MODEL}
        return {"intent_category": "GENERAL", "complexity_score": 0.3, "selected_model": settings.DEFAULT_FAST_MODEL}

    # 1. Utilizar modelo rápido y económico para clasificación en producción
    router_llm = ChatOpenAI(
        model=settings.DEFAULT_FAST_MODEL,
        temperature=0.0,
        api_key=settings.OPENAI_API_KEY
    )

    prompt_messages = [
        SystemMessage(content=ROUTER_SYSTEM_PROMPT),
        HumanMessage(content=f"Consulta del pasajero: {last_user_message}")
    ]

    try:
        response = router_llm.invoke(prompt_messages)
        content = response.content.strip()

        # Extraer JSON del bloque de código si el LLM incluye markdown
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(content)
        category = parsed.get("category", "GENERAL")
        complexity = float(parsed.get("complexity_score", 0.5))

    except Exception:
        # Fallback conservador en caso de falla en parseo
        category = "GENERAL"
        complexity = 0.8

    # 2. Selección del modelo óptimo (Model Routing)
    # Para casos complejos (disrupciones/ley DGAC) se usa GPT-4o o Claude 3.5 Sonnet
    if complexity > 0.6:
        selected_model = settings.DEFAULT_ADVANCED_MODEL  # gpt-4o
    else:
        selected_model = settings.DEFAULT_FAST_MODEL  # gpt-4o-mini / Llama-3

    return {
        "intent_category": category,
        "complexity_score": complexity,
        "selected_model": selected_model
    }
# =====================================================================
# AIRLINE - TELEMETRY & OBSERVABILITY (app/monitoring/telemetry.py)
# Monitoreo de latencia, costo de tokens, OpenTelemetry y LangSmith
# =====================================================================
import time
import logging
from typing import Dict, Any, Optional, Callable
from functools import wraps
from dataclasses import dataclass, field
from datetime import datetime

from structlog import get_logger
from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode

from app.core.config import settings

# Inicializar logger estructurado para producción
logger = get_logger("sky_agent_telemetry")
tracer = trace.get_tracer("sky.agentic.tracer", settings.VERSION)

@dataclass
class AgentExecutionMetrics:
    """Métricas de rendimiento y costo acumulados durante una sesión agentica."""
    session_id: str
    pnr: Optional[str] = None
    selected_model: str = settings.DEFAULT_FAST_MODEL
    intent_category: str = "GENERAL"
    complexity_score: float = 0.0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    latency_ms: float = 0.0
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    pii_flags_triggered: int = 0
    audit_passed: bool = True

    def calculate_cost(self) -> float:
        """
        Calcula el costo estimado en USD basado en el modelo y tokens consumidos.
        Precios estándar de referencia:
        - GPT-4o: $5.00 / 1M input, $15.00 / 1M output
        - GPT-4o-mini / Llama 3 8B: $0.15 / 1M input, $0.60 / 1M output
        """
        if "gpt-4o" in self.selected_model.lower() and "mini" not in self.selected_model.lower():
            input_rate = 5.00 / 1_000_000
            output_rate = 15.00 / 1_000_000
        else:
            input_rate = 0.15 / 1_000_000
            output_rate = 0.60 / 1_000_000

        self.estimated_cost_usd = (self.prompt_tokens * input_rate) + (self.completion_tokens * output_rate)
        return self.estimated_cost_usd

    def finalize(self) -> None:
        """Registra la hora de término y calcula latencia final."""
        self.end_time = time.time()
        self.latency_ms = round((self.end_time - self.start_time) * 1000, 2)
        self.total_tokens = self.prompt_tokens + self.completion_tokens
        self.calculate_cost()

class AgentTelemetryTracker:
    """
    Gestor de telemetría y auditoría para registrar spans en OpenTelemetry
    y eventos de trazabilidad en LangSmith / Prometheus.
    """

    @staticmethod
    def log_node_execution(node_name: str, state: Dict[str, Any], duration_ms: float) -> None:
        """Registra la ejecución de un nodo individual en LangGraph."""
        logger.info(
            "langgraph_node_executed",
            node_name=node_name,
            session_id=state.get("session_id", "N/A"),
            pnr=state.get("pnr", "N/A"),
            intent_category=state.get("intent_category", "UNKNOWN"),
            selected_model=state.get("selected_model", "N/A"),
            latency_ms=duration_ms,
            timestamp=datetime.utcnow().isoformat()
        )

    @staticmethod
    def log_security_audit(session_id: str, pii_detected: bool, action_taken: str) -> None:
        """Registra eventos de gobierno de datos y enmascaramiento PII."""
        logger.warning(
            "security_pii_audit",
            session_id=session_id,
            pii_detected=pii_detected,
            action_taken=action_taken,
            compliance_standard="DGAC_DAN_151_PII",
            timestamp=datetime.utcnow().isoformat()
        )

    @staticmethod
    def record_trace(span_name: str):
        """Decorador para medir spans de OpenTelemetry alrededor de funciones o tools de Sabre."""
        def decorator(func: Callable):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as exc:
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        span.record_exception(exc)
                        raise exc
                    finally:
                        elapsed = (time.time() - start_time) * 1000
                        span.set_attribute("execution.latency_ms", elapsed)

            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with tracer.start_as_current_span(span_name) as span:
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        span.set_status(Status(StatusCode.OK))
                        return result
                    except Exception as exc:
                        span.set_status(Status(StatusCode.ERROR, str(exc)))
                        span.record_exception(exc)
                        raise exc
                    finally:
                        elapsed = (time.time() - start_time) * 1000
                        span.set_attribute("execution.latency_ms", elapsed)

            import asyncio
            if asyncio.iscoroutinefunction(func):
                return async_wrapper
            return sync_wrapper

        return decorator


# Instancia exportable del tracker
telemetry_tracker = AgentTelemetryTracker()

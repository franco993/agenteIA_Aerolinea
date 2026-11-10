# =====================================================================
# AIRLINE - RAG RETRIEVAL ENGINE (app/rag/retriever.py)
# Búsqueda Vectorial Híbrida (Dense Embeddings + Metadata Filtering)
# Normativas Aeronáuticas DGAC Chile DAN 151 y Políticas SKY Airline
# =====================================================================
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models

from app.core.config import settings
from app.monitoring.telemetry import telemetry_tracker

logger = logging.getLogger("sky_rag_retriever")

@dataclass
class RetrievedDocument:
    """Modelo de transferencia de datos para fragmentos normativos recuperados."""
    content: str
    source_law: str  # Ej: "DGAC_DAN_151_ART_32" o "CONTRATO_TRANSPORTE_SKY_CLAUSULA_14"
    similarity_score: float
    metadata: Dict[str, Any]

class SkyLegalRAGRetriever:
    """
    Motor de recuperación RAG (Retrieval-Augmented Generation) especializado en
    leyes aeronáuticas y políticas corporativas de SKY.
    """

    def __init__(self):
        # 1. Inicializar modelo de embeddings oficial de OpenAI
        self.embeddings = OpenAIEmbeddings(
            model=settings.DEFAULT_EMBEDDING_MODEL,
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.collection_name = settings.PGVECTOR_COLLECTION
        self.db_url = settings.DATABASE_URL
        self._vector_store: Optional[PGVector] = None

    def _get_pgvector_instance(self) -> PGVector:
        """Inicialización diferida (lazy initialization) del conector PGvector."""
        if self._vector_store is None:
            try:
                self._vector_store = PGVector(
                    connection_string=self.db_url,
                    embedding_function=self.embeddings,
                    collection_name=self.collection_name
                )
            except Exception as err:
                logger.warning(f"No se pudo conectar a PGvector: {err}. Utilizando modo Fallback en memoria.")
                self._vector_store = None
        return self._vector_store

    @telemetry_tracker.record_trace("pgvector_hybrid_search")
    async def retrieve_relevant_policies(
        self,
        query: str,
        category: str = "GENERAL",
        top_k: int = 3,
        min_similarity: float = 0.72
    ) -> List[RetrievedDocument]:
        """
        Recupera reglamentos y artículos legales relevantes ordenados por similitud vectorial,
        filtrando por categoría de contingencia (DISRUPTION, BAGGAGE, ANCILLARY).
        """
        vector_db = self._get_pgvector_instance()

        # Fallback local determinista si la Base de Datos Vectorial aún no está instanciada localmente
        if vector_db is None:
            return self._get_fallback_regulations(category)

        try:
            # Búsqueda por similitud vectorial con filtro de metadatos en PGvector
            filter_dict = {}
            if category in ["DISRUPTION", "BAGGAGE"]:
                filter_dict = {"category": category}

            docs_with_scores = await vector_db.asimilarity_search_with_score(
                query=query,
                k=top_k,
                filter=filter_dict
            )

            results: List[RetrievedDocument] = []
            for doc, score in docs_with_scores:
                # Convertir distancia L2/Coseno a puntaje de similitud (0.0 a 1.0)
                similarity = round(1.0 - score if score <= 1.0 else 1.0 / (1.0 + score), 3)

                if similarity >= min_similarity:
                    results.append(
                        RetrievedDocument(
                            content=doc.page_content,
                            source_law=doc.metadata.get("source_law", "NORMATIVA_SKY_GENERAL"),
                            similarity_score=similarity,
                            metadata=doc.metadata
                        )
                    )

            # Si no supera el umbral, retornar reglamentos fallback garantizados
            if not results:
                return self._get_fallback_regulations(category)

            return results

        except Exception as exc:
            logger.error(f"Error durante la consulta vectorial a PGvector: {exc}")
            return self._get_fallback_regulations(category)

    def _get_fallback_regulations(self, category: str) -> List[RetrievedDocument]:
        """
        Reglas legales base (DAN 151 DGAC Chile) integradas para garantizar
        respuestas correctas aún ante caída temporal de la DB vectorial.
        """
        fallback_map = {
            "DISRUPTION": [
                RetrievedDocument(
                    content=(
                        "DGAC DAN 151 Art. 32: En cancelaciones o demoras mayores a 3 horas "
                        "imputables a la empresa (mantenimiento/fallas mecánicas), la aerolínea debe "
                        "proporcionar alimentación, llamadas telefónicas y reacomodo en el primer vuelo disponible. "
                        "Si la demora requiere pernoctar, se debe otorgar hotel y traslados sin costo."
                    ),
                    source_law="DGAC_DAN_151_ART_32",
                    similarity_score=0.95,
                    metadata={"category": "DISRUPTION", "imputable": True}
                ),
                RetrievedDocument(
                    content=(
                        "Contrato Transportes SKY Cláusula 14: Compensación monetaria adicional por cancelación "
                        "imputable aplicable según distancia del vuelo (Hasta $150 USD o voucher de viaje equivalente)."
                    ),
                    source_law="SKY_POLICY_COMPENSATION_2026",
                    similarity_score=0.91,
                    metadata={"category": "DISRUPTION"}
                )
            ],
            "BAGGAGE": [
                RetrievedDocument(
                    content=(
                        "Reglamento Equipajes SKY & Convenio de Montreal: Para equipaje no entregado a tiempo en destino, "
                        "el pasajero tiene derecho a emitir un reporte de irregularidad PIR y solicitar un viático de "
                        "gastos de primera necesidad por $50 USD diarios (máximo 3 días)."
                    ),
                    source_law="SKY_BAGGAGE_PIR_POLICY",
                    similarity_score=0.94,
                    metadata={"category": "BAGGAGE", "allowance_per_day": 50.0}
                )
            ],
            "ANCILLARY": [
                RetrievedDocument(
                    content=(
                        "Políticas Tarifarias SKY: Los equipajes de bodega (23kg) y asientos especiales pueden añadirse "
                        "hasta 3 horas antes de la salida del vuelo a través de canales digitales o en counter con tarifa regular."
                    ),
                    source_law="SKY_ANCILLARY_RULES",
                    similarity_score=0.88,
                    metadata={"category": "ANCILLARY"}
                )
            ]
        }

        return fallback_map.get(category, [
            RetrievedDocument(
                content="SKY Términos Generales: Toda solicitud de cambio o devolución está sujeta a las condiciones de la tarifa adquirida.",
                source_law="SKY_TERMS_GENERAL",
                similarity_score=0.80,
                metadata={"category": "GENERAL"}
            )
        ])

# Instancia singleton exportable
sky_rag_retriever = SkyLegalRAGRetriever()
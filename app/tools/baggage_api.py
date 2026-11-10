# =====================================================================
# AIRLINE - WORLDTRACER BAGGAGE TOOLS (app/tools/baggage_api.py)
# Herramientas para registro PIR, rastreo de equipaje e indemnizaciones
# =====================================================================
import logging
from typing import Dict, Any
from datetime import datetime, timedelta
from langchain_core.tools import tool

from app.schemas.baggage import (
    BaggageClaimRequest,
    BaggageTrackingOutput,
    BaggageStatusEnum
)

logger = logging.getLogger("baggage_tools")

@tool("track_baggage_status")
def track_baggage_status(bag_tag_number: str, pnr: str) -> Dict[str, Any]:
    """
    Consulta el estado de rastreo en tiempo real de una maleta en el sistema WorldTracer/Navitaire.
    Recibe el número de etiqueta (ej. 07849920) y el PNR.
    """
    tag_clean = bag_tag_number.replace(" ", "").upper()
    logger.info(f"Rastreando equipaje Tag={tag_clean} para PNR={pnr}")

    # Simulación de respuesta de API de equipajes WorldTracer
    mock_bag_db = {
        "07849920": {
            "pir_number": "SCLH298402",
            "bag_tag_number": "07849920",
            "current_status": BaggageStatusEnum.IN_TRANSIT,
            "last_known_location": "SCL (Aeropuerto Pudahuel - Santiago)",
            "estimated_delivery": (datetime.utcnow() + timedelta(hours=14)).isoformat(),
            "allow_daily_allowance": True,
            "daily_allowance_amount_usd": 50.0
        }
    }

    if tag_clean in mock_bag_db:
        return {
            "found": True,
            "details": mock_bag_db[tag_clean],
            "message": "Equipaje localizado en tránsito a su destino."
        }

    return {
        "found": False,
        "details": None,
        "message": f"No se encontraron registros de escaneo para la etiqueta {tag_clean}."
    }


@tool("create_baggage_pir_claim", args_schema=BaggageClaimRequest)
def create_baggage_pir_claim(
    pnr: str,
    bag_tag_number: str,
    passenger_rut_dni: str,
    delivery_address: str,
    bag_description: str
) -> Dict[str, Any]:
    """
    Crea un Parte de Irregularidad de Equipaje (Formulario PIR) en WorldTracer
    y genera la orden de despacho a domicilio junto con la tarjeta de viático de $50 USD.
    """
    pnr_upper = pnr.upper().strip()
    tag_clean = bag_tag_number.replace(" ", "").upper()
    pir_code = f"SCLH2{tag_clean[-5:]}"

    logger.info(f"Generando PIR={pir_code} para PNR={pnr_upper}, Tag={tag_clean}")

    return {
        "success": True,
        "pir_number": pir_code,
        "pnr": pnr_upper,
        "bag_tag_number": tag_clean,
        "assigned_delivery_address": delivery_address,
        "daily_allowance_voucher": f"VOUCHER-PIR-{pir_code}-50USD",
        "instructions": (
            f"El reclamo PIR {pir_code} se ha registrado con éxito. "
            "Se ha enviado un voucher digital de $50 USD a su correo para compras de primera necesidad. "
            "La maleta será despachada a la dirección registrada dentro de las próximas 24 horas."
        )
    }
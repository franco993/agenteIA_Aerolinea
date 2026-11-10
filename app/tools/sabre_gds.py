# =====================================================================
# AIRLINE - SABRE GDS INTEGRATION TOOLS (app/tools/sabre_gds.py)
# Herramientas tipadas (@tool) para consulta PNR, reasignación y vouchers
# =====================================================================
import logging
from typing import Dict, Any, Optional
from datetime import datetime, date
from langchain_core.tools import tool

from app.schemas.flight import (
    PNRQueryRequest,
    FlightRebookingInput,
    FlightRebookingOutput,
    FlightSegment,
    FlightStatusEnum,
    DisruptionReasonEnum
)
from app.monitoring.telemetry import telemetry_tracker

logger = logging.getLogger("sabre_gds_tools")


@tool("query_sabre_pnr", args_schema=PNRQueryRequest)
def query_sabre_pnr(pnr: str, last_name: str) -> Dict[str, Any]:
    """
    Consulta el estado de una reserva (PNR) en el GDS Sabre / Navitaire.
    Retorna la lista de segmentos de vuelo, pasajero titular y estado actual.
    """
    logger.info(f"Invocando API Sabre GDS para PNR={pnr}, Pasajero={last_name}")

    # Simulación de respuesta de Sabre Web Services / SOAP Client
    # En producción conecta vía zeep a Sabre Bargain Finder Max o Passenger Details API
    mock_pnr_db = {
        "SKY98A": {
            "passenger_name": f"Juan {last_name.capitalize()}",
            "pnr": "SKY98A",
            "status": "CONFIRMED",
            "segments": [
                {
                    "flight_number": "H2-104",
                    "origin": "SCL",
                    "destination": "ANF",
                    "departure_time": "2026-11-10T08:30:00",
                    "arrival_time": "2026-11-10T10:30:00",
                    "status": "CANCELLED",
                    "disruption_reason": "MAINTENANCE",
                    "aircraft_type": "Airbus A320neo"
                }
            ]
        }
    }

    pnr_upper = pnr.upper().strip()
    if pnr_upper in mock_pnr_db:
        return {
            "found": True,
            "data": mock_pnr_db[pnr_upper],
            "message": "PNR encontrado exitosamente en Sabre GDS."
        }

    return {
        "found": False,
        "data": None,
        "message": f"No se encontró ninguna reserva activa con el PNR {pnr_upper} para el apellido {last_name}."
    }


@tool("rebook_flight_sabre", args_schema=FlightRebookingInput)
def rebook_flight_sabre(
        pnr: str,
        original_flight_number: str,
        new_flight_number: str,
        new_departure_date: date,
        issue_hotel_voucher: bool = False,
        issue_meal_voucher: bool = True,
        compensation_amount_usd: float = 0.0
) -> Dict[str, Any]:
    """
    Reagenda un vuelo cancelado o demorado en Sabre GDS y emite vouchers de
    asistencia (alimentación/hotel) e indemnizaciones monetarias si corresponde por DGAC.
    """
    logger.info(f"Reagendando PNR={pnr} a vuelo {new_flight_number} en fecha {new_departure_date}")

    pnr_upper = pnr.upper().strip()
    timestamp_str = datetime.utcnow().strftime("%Y%m%d%H%M")

    e_ticket_number = f"078-{timestamp_str}-99"
    hotel_code = f"HTL-SKY-{pnr_upper}-2026" if issue_hotel_voucher else None
    meal_code = f"MEAL-SKY-{pnr_upper}-50USD" if issue_meal_voucher else None

    output = FlightRebookingOutput(
        success=True,
        pnr=pnr_upper,
        new_e_ticket=e_ticket_number,
        hotel_voucher_code=hotel_code,
        meal_voucher_code=meal_code,
        status_message=(
            f"Vuelo reagendado con éxito a {new_flight_number}. "
            f"E-Ticket emitido: {e_ticket_number}."
        )
    )

    return output.model_dump()
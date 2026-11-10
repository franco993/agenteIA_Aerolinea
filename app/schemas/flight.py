# =====================================================================
# AIRLINE - FLIGHT & PNR SCHEMAS (app/schemas/flight.py)
# Modelos de validación Pydantic v2 para consultas y operaciones GDS
# =====================================================================

from typing import List, Optional, Dict, Any
from datetime import datetime, datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

class FlightStatusEnum(str, Enum):
    SCHEDULED = "SCHEDULED"
    ON_TIME = "ON_TIME"
    DELAYED = "DELAYED"
    CANCELLED = "CANCELLED"
    BOARDING = "BOARDING"
    IN_FLIGHT = "IN_FLIGHT"
    ARRIVED = "ARRIVED"

class DisruptionReasonEnum(str, Enum):
    MAINTENANCE = "MAINTENANCE"         # Imputable a la Aerolínea
    WEATHER = "WEATHER"                 # No Imputable (fuerza mayor)
    CREW_REST = "CREW_REST"             # Imputable a la Aerolínea
    AIR_TRAFFIC_CONTROL = "ATC"         # No Imputable
    UNKNOWN = "UNKNOWN"

# --- 1. SOLICITUD DE CONSULTA PNR ---
class PNRQueryRequest(BaseModel):
    prn: str = Field(..., min_length=6, max_length=6, description="Código de Reserva alfanumérico (ej: SKY98A)")
    last_name: str = Field(..., min_length=2, max_length=50, description="Apellido del Pasajero Principal")

    @field_validator('pnr')
    @classmethod
    def validate_pnr_format(cls, v: str) -> str:
        v_upper = v.upper().strip()
        if not v_upper.isalnum():
            raise ValueError("El PNR debe contener solo caracteres alfanuméricos")
        return v_upper

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "pnr": "SKY98A",
            "last_name": "Mendoza"
        }
    })

# --- 2. DETALLES DE VUELO & ITINERARIO ---
class FlightSegment(BaseModel):
    flight_number: str = Field(..., description="Número de Vuelo con Prefijo de Aerolínea (ej: H2 - 104)")
    origin: str = Field(..., min_length=3, max_length=3, description="Código IATA origen (ej: SCL)")
    destination: str = Field(..., min_length=3, max_length=3, description="Código IATA destino (ej: ANF)")
    departure_time: datetime
    arrival_time: datetime
    status: FlightStatusEnum
    disruption_reason: Optional[DisruptionReasonEnum] = None
    aircraft_type: str = Field(default="Airbus A320neo")

# --- 3. REASIGNACION DE VUELO (TOOL INPUT FOR SABRE) ---
class FlightRebookingInput(BaseModel):
    pnr: str = Field(..., min_length=6, max_length=6)
    original_flight_number: str
    new_flight_number: str
    new_departure_date: datetime
    issue_hotel_voucher: bool = Field(default=False, description="Emitir voucher si la demora > 6h nocturnas")
    issue_meal_voucher: bool = Field(default=True, description="Emitir voucher de alimentación")
    compensation_amount_usd: float = Field(default=0.0, ge=0.0, le=500.0, description="Monto indemnización según DGAC")

class FlightRebookingOutput(BaseModel):
    success: bool
    pnr: str
    new_e_ticket: str
    hotel_voucher_code: Optional[str] = None
    meal_voucher_code: Optional[str] = None
    status_message: str
    processed_at: datetime = Field(default_factory=datetime.utcnow)

# =====================================================================
# AIRLINE - BAGGAGE SCHEMAS (app/schemas/baggage.py)
# Modelos de validación Pydantic v2 para rastreo e indemnización PIR
# =====================================================================
from typing import List, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict


class BaggageStatusEnum(str, Enum):
    CHECKED_IN = "CHECKED_IN"
    LOADED = "LOADED"
    IN_TRANSIT = "IN_TRANSIT"
    DELAYED = "DELAYED"
    LOST = "LOST"
    FOUND_READY_FOR_DELIVERY = "FOUND_READY_FOR_DELIVERY"
    DELIVERED = "DELIVERED"


# --- 1. RECLAMO DE EQUIPAJE EXTRAVIADO (PIR - Property Irregularity Report) ---
class BaggageClaimRequest(BaseModel):
    pnr: str = Field(..., min_length=6, max_length=6, description="Código PNR de la Reserva")
    bag_tag_number: str = Field(..., min_length=8, max_length=12,
                                description="Número de etiqueta de maleta (ej: 07849920)")
    passenger_rut_dni: str = Field(..., description="Documento de identidad del titular")
    delivery_address: str = Field(..., min_length=10, max_length=200,
                                  description="Dirección para despacho de maleta una vez hallada")
    bag_description: str = Field(..., min_length=5, max_length=300,
                                 description="Color, marca y características distintivas de la maleta")

    @field_validator('bag_tag_number')
    @classmethod
    def clean_tag_number(cls, v: str) -> str:
        return v.replace(" ", "").upper()

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "pnr": "SKY77B",
            "bar_tag_number": "07849920"
                              "passenger_rut_dni:" "18.452.910-k",
            "delivery_address": "Av. Larco 456, Miraflores, Lima",
            "bag_description": "Maleta rígida negra de 23Kg con cinta roja"
        }
    })


# --- 2. RESPUESTA DEL RASTREO DE EQUIPAJE (NAVITAIRE / WORLDTRACER) ---
class BaggageTrackingOutput(BaseModel):
    pir_number: str = Field(..., description="Código oficial de reclamo PIR (ej: LIMH210492)")
    bag_tag_number: str
    current_status: BaggageStatusEnum
    last_known_location: str = Field(..., description="Estación / Aeropuerto donde fue escaneada por última vez")
    estimated_delivery: Optional[datetime] = None
    allow_daily_allowance: bool = Field(default=True, description="Derecho a fondo de gastos de primera necesidad")
    daily_allowance_amount_usd: float = Field(default=50.0, description="Monto diario para kit de aseo/ropa")

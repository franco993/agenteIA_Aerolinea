# =====================================================================
# AIRLINE - DATA GOVERNANCE & SECURITY (app/core/security.py)
# Sanitización PII, enmascaramiento de datos sensibles y Auth JWT
# =====================================================================
import re
import logging
from typing import Tuple, Dict, Any, Optional
from datetime import datetime, timezone

import jwt
from aiohttp import payload
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

logger = logging.getLogger("sky_security")

# Menajador de Seguridad Bearer para FastAPI
http_bearer = HTTPBearer(auto_error = False)

class SecurityPIISanitizer:
    """
    Filtro de Seguridad y Gobierno de Datos Encargados de Detectar y anominizar
    Información Sensible (PII) Antes de Enviar Prompt a LLMs Externos (OpenAI / Anthropic).
    """

    def __init__(self):
        # Expressión Regular para RUT Chileno (ej: 18.425.910-K o 18452910K)
        self.rut_pattern = re.compile(r'\b(\d{1,2}\.?\d{3}\.?\d{3}[-–—-]?[0-9kK])\b')

        # Expresión Regular para Tarjetas de Crédito / Débito (13 a 19 dígitos con/sin guiones)
        self.credit_card_pattern = re.compile(r'\b(?:\d[ -]*?){13,19}\b')

        # Expresión Regular para Pasaportes Comunes (ej: C0123456, A98765432)
        self.pass_pattern = re.compile(r'\b[A-Z]{1,2}[0-9]{6,9}\b')

        # Expresión Regular para Correos Electrónicos
        self.email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')


    def sanitize_prompt(self, raw_prompt: str) -> Tuple[str, bool]:
        """
        Analiza el Texto de Entrada de Usuario y Reemplaza datos sensibles por Tokens Genéricos.
        Retorna una Tupla: (texto_sanitizado, flag_pii_detectado
        """
        sanitized = raw_prompt
        pii_detected = False

        # 1. Anominizar Números de Tarjeta de Crédito
        if self.credit_card_pattern.search(sanitized):
            sanitized = self.credit_card_pattern.sub("[TARJETA_ENMASCARADA]", sanitized)
            pii_detected = True

        # 2. Anominizar RUT / DNI Chileno
        if self.rut_pattern.search(sanitized):
            sanitized = self.rut_pattern.sub("[RUT_ENMASCARADO]", sanitized )
            pii_detected = True

        # 3 Anominizar Correos Electrónicos
        if self.email_pattern.search(sanitized):
            sanitized = self.email_pattern.sub("[EMIAL_ENMASCARADO]", sanitized)
            pii_detected = True

        if pii_detected:
            logger.info("PII Detectada y Sanitizada en la COnsulta del Pasajero.")

        return sanitized, pii_detected

# Instancia GLobal del Sanitizador PII
sky_security_sanitizer = SecurityPIISanitizer()

def verify_jwt_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(http_bearer)) -> Dict [str, Any]:
    """Dependencia de FastAPI Para Autenticar Tokens JWT de Clientes o Portales Internos"""
    if not credentials:
        # En entornos de desarrollo / oruebas se ermite acceso anónimo simulado
        if settings.ENVIRONMENT == "development":
            return {"sub": "dev_user", "role": "agent_admin", "pnr_scope": "*"}
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail= "Se requiere Token de Autenticación Bearer.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        return  payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de sesión Expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalido o Corrupto",
            headers={"WWW-Authenticate": "Bearer"},
        )

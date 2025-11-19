# domain/models/employee.py
from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field, EmailStr


class Employee(BaseModel):
    """
    Modelo de dominio alineado con Core-v3-Employee (/core/v3/employees),
    con validación laxa para tolerar valores no documentados.
    """
    id: Optional[str] = Field(default=None)
    first_name: Optional[str] = None
    last_name: Optional[str] = None

    # Emails
    email: Optional[EmailStr] = None          # campo principal en v3
    personal_mail: Optional[EmailStr] = None  # personalMail

    # Estado y datos básicos
    status: Optional[str] = None                  # active/inactive/otros
    work_status: Optional[str] = None             # online/offline/paused/remote/otros
    image_profile_url: Optional[str] = None
    code: Optional[int] = None
    pin: Optional[int] = None
    phone: Optional[str] = None
    work_phone: Optional[str] = None

    # Compañía (datos principales, aplanados)
    company_id: Optional[str] = None
    company_name: Optional[str] = None
    company_notification_email: Optional[EmailStr] = None
    company_language: Optional[str] = None
    company_created_at: Optional[datetime] = None
    company_updated_at: Optional[datetime] = None

    # Datos administrativos
    gender: Optional[str] = None                  # female/male/no_response/otros
    contract_id: Optional[str] = None
    nid: Optional[str] = None
    identity_number_type: Optional[str] = None    # dni/nie/rut/other/otros
    ssn: Optional[str] = None
    price_per_hour: Optional[float] = None
    account_number: Optional[str] = None

    # Fechas
    date_of_birth: Optional[date] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # Datos personales ampliados
    children: Optional[int] = None
    disability: Optional[int] = None
    address: Optional[str] = None
    postal_code: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    country: Optional[str] = None
    nationality: Optional[str] = None            # (deprecated por la API)
    nationalities: Optional[List[str]] = None

    # Otros
    marital_status: Optional[str] = None
    emergency_phone: Optional[str] = None
    description: Optional[str] = None
    salary_range: Optional[str] = None
    study_level: Optional[str] = None
    professional_category_code: Optional[str] = None
    professional_category_description: Optional[str] = None
    bic: Optional[str] = None
    job_charge_id: Optional[str] = None
    job_charge_name: Optional[str] = None
    language: Optional[str] = None
    nfc: Optional[str] = None

    # Recruiter principal (aplanado)
    main_recruiter_id: Optional[str] = None
    main_recruiter_first_name: Optional[str] = None
    main_recruiter_last_name: Optional[str] = None
    main_recruiter_image_profile_url: Optional[str] = None
    main_recruiter_email: Optional[EmailStr] = None
    main_recruiter_work_status: Optional[str] = None
    main_recruiter_work_check_type_color: Optional[str] = None
    main_recruiter_work_check_type_name: Optional[str] = None

    # Custom fields
    custom_fields: Optional[List[Dict[str, Any]]] = None

    model_config = {"extra": "allow"}

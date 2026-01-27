from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class SurveyBasicInfo(BaseModel):
    title: str
    type: str
    status: str
    createdAt: datetime
    updatedAt: datetime


class UserAgentInfo(BaseModel):
    browser: Optional[str] = None
    os: Optional[str] = None
    device: Optional[str] = None


class SurveyMeta(BaseModel):
    url: str
    userAgent: UserAgentInfo


class WebhookData(BaseModel):
    id: str
    createdAt: datetime
    updatedAt: datetime
    surveyId: str
    displayId: Optional[str] = None
    contact: Optional[Any] = None
    contactAttributes: Optional[Any] = None
    finished: bool
    endingId: Optional[str] = None
    data: Dict[str, Any]
    variables: Dict[str, Any]
    ttc: Dict[str, float]
    tags: List[str]
    meta: SurveyMeta
    singleUseId: Optional[str] = None
    language: Optional[str] = None
    survey: SurveyBasicInfo


class WebhookPayload(BaseModel):
    webhookId: Optional[str] = None
    event: str
    data: Optional[WebhookData] = None


class WebhookResponse(BaseModel):
    id: int
    status: str


# --- Checkout & Woovi ---

class CheckoutRequest(BaseModel):
    name: str
    email: str
    whatsapp: str
    cpf: str


class ChargeResponse(BaseModel):
    id: int
    correlation_id: str
    status: str
    br_code: Optional[str] = None
    qr_code_url: Optional[str] = None
    payment_link_url: Optional[str] = None
    value: int
    expires_at: Optional[datetime] = None


class WooviCharge(BaseModel):
    status: str
    correlationID: str


class WooviWebhookPayload(BaseModel):
    event: str
    charge: Optional[WooviCharge] = None
    data_criacao: Optional[datetime] = None
    evento: Optional[str] = None


class CalAttendee(BaseModel):
    name: str
    email: str
    phoneNumber: Optional[str] = None


class CalOrganizer(BaseModel):
    name: str
    email: str


class CalPayload(BaseModel):
    bookingId: Optional[int] = None
    title: Optional[str] = None
    attendees: Optional[List[CalAttendee]] = None
    organizer: Optional[CalOrganizer] = None


class CalWebhookPayload(BaseModel):
    triggerEvent: str
    payload: Optional[CalPayload] = None

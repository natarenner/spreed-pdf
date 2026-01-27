import json
from typing import Any
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from api.settings import api_settings

from db.session import get_db
from db.models import WebhookRequest, Charge
from api.schemas import WebhookPayload, WebhookResponse, WooviWebhookPayload, CalWebhookPayload
from workers.tasks import (
    process_webhook, 
    send_purchase_confirmation_whatsapp, 
    send_cal_booking_confirmation_whatsapp,
    track_purchase_ploomes_task,
    track_booking_ploomes_task
)


router = APIRouter()


@router.get("/health")
def health_check():
    return {"status": "ok"}


@router.post("/webhooks/form", response_model=WebhookResponse)
def receive_webhook(payload: WebhookPayload, db: Session = Depends(get_db)):
    if payload.event == "testEndpoint":
        return WebhookResponse(id=0, status="ok")

    record = WebhookRequest(payload=payload.model_dump(mode="json"), status="queued")
    db.add(record)
    db.commit()
    db.refresh(record)

    process_webhook.send(record.id)

    return WebhookResponse(id=record.id, status=record.status)


@router.post("/webhooks/woovi")
async def woovi_webhook(request: Request, db: Session = Depends(get_db)):
    # Validação do Token de Segurança
    if api_settings.woovi_webhook_token:
        auth_header = request.headers.get("Authorization")
        if auth_header != api_settings.woovi_webhook_token:
            print(f"Tentativa de webhook não autorizada. Header: {auth_header}")
            raise HTTPException(status_code=401, detail="Unauthorized")

    body = await request.body()
    try:
        data = json.loads(body)
        # Se os dados vierem como uma string (double encoding), fazemos o load novamente
        if isinstance(data, str):
            data = json.loads(data)
    except Exception as e:
        print(f"Erro ao parsear JSON da Woovi: {e}")
        return {"status": "error", "message": "invalid json"}

    try:
        payload = WooviWebhookPayload(**data)
    except Exception as e:
        print(f"Erro de validação do webhook Woovi: {e}")
        return {"status": "error", "message": "invalid payload structure"}

    if payload.evento == "teste_webhook":
        return {"status": "ok", "message": "ping received"}

    if payload.event == "OPENPIX:CHARGE_COMPLETED" and payload.charge:
        print(payload)
        # Find the charge by correlationID
        correlation_id = payload.charge.correlationID
        charge = db.query(Charge).filter(Charge.correlation_id == correlation_id).first()

        if charge:
            charge.status = "completed"
            db.commit()
            print(f"Iniciando outra ação pos compra para {charge.correlation_id}")
            
            # Envia mensagem no WhatsApp via BotConversa
            send_purchase_confirmation_whatsapp.send(charge.id)
            
            # Registra no Ploomes
            track_purchase_ploomes_task.send(charge.id)
            
    return {"status": "ok"}


@router.post("/webhooks/cal")
async def cal_webhook(payload: CalWebhookPayload):
    print(f"Webhook Cal.com recebido: {payload.triggerEvent}")
    
    if payload.triggerEvent == "PING":
        return {"status": "ok", "message": "pong"}

    if payload.triggerEvent == "BOOKING_CREATED" and payload.payload:
        # Cal.com pode ter múltiplos participantes, pegamos o primeiro
        if payload.payload.attendees:
            customer = payload.payload.attendees[0]
            organizer_email = payload.payload.organizer.email if payload.payload.organizer else ""
            
            if customer.phoneNumber:
                # 1) WhatsApp
                send_cal_booking_confirmation_whatsapp.send(
                    phone=customer.phoneNumber,
                    name=customer.name
                )
                
                # 2) Ploomes Tracking
                track_booking_ploomes_task.send(
                    name=customer.name,
                    email=customer.email,
                    phone=customer.phoneNumber,
                    organizer_email=organizer_email
                )
            else:
                print(f"Cal.com: Cliente {customer.name} sem número de telefone no agendamento.")
                
    return {"status": "ok"}

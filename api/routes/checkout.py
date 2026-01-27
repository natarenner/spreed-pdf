import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from db.session import get_db
from db.models import Charge
from api.schemas import CheckoutRequest, ChargeResponse
from workers.tasks import create_woovi_charge_task

router = APIRouter()

@router.post("/checkout", response_model=ChargeResponse)
def create_checkout(payload: CheckoutRequest, db: Session = Depends(get_db)):
    # Create a unique correlation ID
    correlation_id = str(uuid.uuid4())
    
    # Store charge in DB (pending)
    charge = Charge(
        correlation_id=correlation_id,
        value=10000,  # R$ 100,00 fixed for now
        customer_name=payload.name,
        customer_email=payload.email,
        customer_tax_id=payload.cpf,
        customer_phone=payload.whatsapp,
        status="pending"
    )
    db.add(charge)
    db.commit()
    db.refresh(charge)
    
    # Queue Woovi API call
    create_woovi_charge_task.send(charge.id)
    
    return charge

@router.get("/checkout/{charge_id}", response_model=ChargeResponse)
def get_checkout_status(charge_id: int, db: Session = Depends(get_db)):
    charge = db.get(Charge, charge_id)
    if not charge:
        raise HTTPException(status_code=404, detail="Charge not found")
    
    return charge

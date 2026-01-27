import requests
from typing import Any, Dict, Optional
from api.settings import api_settings

BOTCONVERSA_BASE_URL = "https://backend.botconversa.com.br/api/v1/webhook"

def get_headers() -> Dict[str, str]:
    if not api_settings.botconversa_api_key:
        raise ValueError("BOTCONVERSA_API_KEY not configured")
    return {
        "API-KEY": api_settings.botconversa_api_key,
        "Content-Type": "application/json"
    }

def get_subscriber_by_phone(phone: str) -> Optional[Dict[str, Any]]:
    """
    Find subscriber by phone number.
    Returns Subscriber object if found, else None.
    """
    import re
    clean_phone = re.sub(r'\D', '', str(phone))
    
    # Se o número tiver 10 ou 11 dígitos (DD + número), adicionamos o 55 (Brasil)
    if len(clean_phone) in [10, 11] and not clean_phone.startswith('55'):
        clean_phone = '55' + clean_phone
    
    url = f"{BOTCONVERSA_BASE_URL}/subscriber/get_by_phone/{clean_phone}/"
    
    response = requests.get(url, headers=get_headers(), timeout=10)
    
    if response.status_code == 404:
        return None
        
    response.raise_for_status()
    return response.json()

def create_subscriber(phone: str, first_name: str, last_name: str = "") -> Dict[str, Any]:
    """
    Create a new subscriber in BotConversa.
    """
    import re
    clean_phone = re.sub(r'\D', '', str(phone))
    
    # Garante o prefixo 55 se for um número brasileiro sem prefixo
    if len(clean_phone) in [10, 11] and not clean_phone.startswith('55'):
        clean_phone = '55' + clean_phone
    
    url = f"{BOTCONVERSA_BASE_URL}/subscriber/"
    payload = {
        "phone": clean_phone,
        "first_name": first_name or "Cliente",
        "last_name": last_name,
        "has_opt_in_whatsapp": True
    }
    
    print(f"BOTCONVERSA: Tentando criar assinante com payload: {payload}")
    
    response = requests.post(url, json=payload, headers=get_headers(), timeout=10)
    
    if not response.ok:
        print(f"BOTCONVERSA CREATE ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()
        
    return response.json()

def send_whatsapp_message(subscriber_id: int, message: str) -> Dict[str, Any]:
    """
    Send a WhatsApp message to a subscriber.
    """
    url = f"{BOTCONVERSA_BASE_URL}/subscriber/{subscriber_id}/send_message/"
    payload = {
        "type": "text",
        "value": message
    }
    
    response = requests.post(url, json=payload, headers=get_headers(), timeout=10)
    response.raise_for_status()
    return response.json()

def ensure_subscriber_and_send_message(phone: str, first_name: str, message: str) -> Dict[str, Any]:
    """
    Ensures subscriber exists (gets ID) and then sends message.
    """
    # 1) Search
    subscriber = get_subscriber_by_phone(phone)
    
    if not subscriber:
        # 2) Create
        subscriber = create_subscriber(phone, first_name)
        
    subscriber_id = subscriber.get("id")
    if not subscriber_id:
        raise ValueError(f"Failed to get subscriber ID for phone {phone}")
        
    # 3) Send Message
    return send_whatsapp_message(subscriber_id, message)

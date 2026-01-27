import requests
from typing import Any, Dict
from api.settings import api_settings

WOOVI_PROD_URL = "https://api.woovi.com/api/v1"
WOOVI_SANDBOX_URL = "https://api.woovi-sandbox.com/api/v1"

def create_pix_charge(charge_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Creates a Pix charge in Woovi.
    """
    if not api_settings.woovi_app_id:
        raise ValueError("WOOVI_APP_ID not configured")

    # Determine URL based on key or settings
    base_url = WOOVI_PROD_URL
    if api_settings.woovi_env.lower() == 'sandbox' or (api_settings.woovi_app_id and "sandbox" in api_settings.woovi_app_id.lower()):
        base_url = WOOVI_SANDBOX_URL

    headers = {
        "Authorization": api_settings.woovi_app_id,
        "Content-Type": "application/json"
    }
    
    # Woovi expects payload:
    # {
    #   "correlationID": "...",
    #   "value": 1000,
    #   "customer": { "name": "...", "taxID": "...", "email": "...", "phone": "..." }
    # }
    
    response = requests.post(
        f"{base_url}/charge",
        json=charge_data,
        headers=headers,
        timeout=10
    )
    
    if not response.ok:
        # Se já existe, tentamos buscar a cobrança existente
        if response.status_code == 400 and "Já existe uma cobrança" in response.text:
            return get_pix_charge(charge_data["correlationID"])
        print(f"WOOVI ERROR ({response.status_code}): {response.text}")
    
    response.raise_for_status()
    return response.json()

def get_pix_charge(correlation_id: str) -> Dict[str, Any]:
    """
    Fetches a charge from Woovi by its correlationID.
    """
    if not api_settings.woovi_app_id:
        raise ValueError("WOOVI_APP_ID not configured")

    base_url = WOOVI_PROD_URL
    if api_settings.woovi_env.lower() == 'sandbox' or "sandbox" in api_settings.woovi_app_id.lower():
        base_url = WOOVI_SANDBOX_URL

    headers = {
        "Authorization": api_settings.woovi_app_id,
    }
    
    # Woovi GET /charge/{correlationID}
    response = requests.get(
        f"{base_url}/charge/{correlation_id}",
        headers=headers,
        timeout=10
    )
    
    response.raise_for_status()
    data = response.json()
    
    # Normalizamos para o worker sempre encontrar a chave "charge"
    if "charge" not in data:
        return {"charge": data}
    return data


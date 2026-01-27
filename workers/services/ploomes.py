import requests
import re
from typing import Any, Dict, List, Optional
from api.settings import api_settings

PLOOMES_BASE_URL = "https://api2.ploomes.com"

def get_headers() -> Dict[str, str]:
    if not api_settings.ploomes_user_key:
        raise ValueError("PLOOMES_USER_KEY not configured")
    return {
        "User-Key": api_settings.ploomes_user_key,
        "Content-Type": "application/json"
    }

def get_user_id_by_email(email: str) -> Optional[int]:
    """
    Finds a Ploomes user ID by email.
    """
    url = f"{PLOOMES_BASE_URL}/Users"
    params = {
        "$select": "Id,Email",
        "$filter": f"Email eq '{email}'"
    }
    response = requests.get(url, headers=get_headers(), params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    value = data.get("value", [])
    if value:
        return value[0].get("Id")
    return None

def get_contact_id_by_email(email: str) -> Optional[int]:
    """
    Finds a Ploomes contact ID by email.
    """
    url = f"{PLOOMES_BASE_URL}/Contacts"
    params = {
        "$select": "Id,Email",
        "$filter": f"Email eq '{email}'"
    }
    response = requests.get(url, headers=get_headers(), params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    
    value = data.get("value", [])
    if value:
        return value[0].get("Id")
    return None

def create_contact(name: str, email: str, phone: str = "") -> int:
    """
    Creates a contact in Ploomes.
    """
    # Basic phone cleaning: remove + and 55 if present at start. 
    # Ploomes is picky with phone formats.
    clean_phone = re.sub(r'\D', '', phone) # Remove tudo que não é número
    if clean_phone.startswith('55'):
        clean_phone = clean_phone[2:]
    
    payload = {
        "Name": name,
        "Email": email,
        "OriginId": 110170856,
        "TypeId": 1, # Person
    }

    if clean_phone:
        payload["Phones"] = [
            {
                "PhoneNumber": clean_phone,
                "TypeId": 0,
                "CountryId": 55
            }
        ]
    
    url = f"{PLOOMES_BASE_URL}/Contacts"
    response = requests.post(url, json=payload, headers=get_headers(), timeout=10)
    
    if not response.ok:
        print(f"PLOOMES CONTACT ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()
        
    data = response.json()
    value = data.get("value", [])
    if value:
        return value[0].get("Id")
    raise ValueError(f"Failed to create contact in Ploomes: {data}")

def create_deal(
    title: str, 
    contact_id: int, 
    stage_id: int, 
    next_owner_id: Optional[int] = None
) -> int:
    """
    Creates a deal in Ploomes.
    """
    payload = {
        "Title": title,
        "ContactId": contact_id,
        "PipelineId": 110029265,
        "StageId": stage_id,
        "OriginId": 110170856,
        "OwnerId": 110053432,
    }
    
    if next_owner_id:
        payload["OtherProperties"] = [
            {
                "FieldKey": "deal_ECD431A9-E30F-4014-A6FF-56A953F1F984",
                "IntegerValue": next_owner_id
            }
        ]
        
    url = f"{PLOOMES_BASE_URL}/Deals"
    response = requests.post(url, json=payload, headers=get_headers(), timeout=10)

    if not response.ok:
        print(f"PLOOMES DEAL ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()

    data = response.json()
    value = data.get("value", [])
    if value:
        return value[0].get("Id")
    raise ValueError(f"Failed to create deal in Ploomes: {data}")

def update_deal(
    deal_id: int, 
    stage_id: Optional[int] = None, 
    next_owner_id: Optional[int] = None
) -> None:
    """
    Updates an existing deal in Ploomes.
    """
    payload = {
        "OriginId": 110170856 # Garante que a origem seja mantida/setada no update
    }
    if stage_id:
        payload["StageId"] = int(stage_id)
    
    if next_owner_id:
        payload["OtherProperties"] = [
            {
                "FieldKey": "deal_ECD431A9-E30F-4014-A6FF-56A953F1F984",
                "IntegerValue": int(next_owner_id)
            }
        ]
        
    url = f"{PLOOMES_BASE_URL}/Deals({deal_id})"
    response = requests.patch(url, json=payload, headers=get_headers(), timeout=10)
    
    if not response.ok:
        print(f"PLOOMES UPDATE ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()

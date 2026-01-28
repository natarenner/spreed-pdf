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
    next_owner_id: Optional[int] = None,
    revenue_range: Optional[str] = None
) -> None:
    """
    Updates an existing deal in Ploomes.
    Can update stage, next owner, and revenue range.
    """
    payload = {
        "OriginId": 110170856 # Garante que a origem seja mantida/setada no update
    }
    if stage_id:
        payload["StageId"] = int(stage_id)
    
    other_properties = []
    
    if next_owner_id:
        other_properties.append({
            "FieldKey": "deal_ECD431A9-E30F-4014-A6FF-56A953F1F984",
            "IntegerValue": int(next_owner_id)
        })
    
    if revenue_range:
        revenue_id = map_revenue_to_ploomes_id(revenue_range)
        if revenue_id:
            other_properties.append({
                "FieldKey": "deal_11082450",  # Table ID for revenue field
                "IntegerValue": revenue_id
            })
    
    if other_properties:
        payload["OtherProperties"] = other_properties
        
    url = f"{PLOOMES_BASE_URL}/Deals({deal_id})"
    response = requests.patch(url, json=payload, headers=get_headers(), timeout=10)
    
    if not response.ok:
        print(f"PLOOMES UPDATE ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()


def map_revenue_to_ploomes_id(revenue_text: str) -> Optional[int]:
    """
    Maps revenue range text to Ploomes table option ID.
    
    Revenue field: contact_F713F5E5-D54A-4CD1-A358-B266BE0719FA
    Options:
    - Até 10 mil -> 1138221110
    - R$ 10-25 mil -> 1138221111
    - R$ 25-50 mil -> 1138221112
    - R$ 50-200 mil -> 1138221113
    - R$ 200 mil+ -> 1138221114
    """
    revenue_lower = revenue_text.lower().strip()
    
    # Mapping based on common patterns
    if "até 10" in revenue_lower or "10 mil" in revenue_lower and "25" not in revenue_lower:
        return 1138221110
    elif "10" in revenue_lower and "25" in revenue_lower:
        return 1138221111
    elif "25" in revenue_lower and "50" in revenue_lower:
        return 1138221112
    elif "50" in revenue_lower and "200" in revenue_lower:
        return 1138221113
    elif "200" in revenue_lower and ("mil+" in revenue_lower or "acima" in revenue_lower):
        return 1138221114
    
    # Fallback: try to extract numbers and determine range
    import re
    numbers = re.findall(r'\d+', revenue_text)
    if numbers:
        first_num = int(numbers[0])
        if first_num < 10:
            return 1138221110
        elif 10 <= first_num < 25:
            return 1138221111
        elif 25 <= first_num < 50:
            return 1138221112
        elif 50 <= first_num < 200:
            return 1138221113
        elif first_num >= 200:
            return 1138221114
    
    print(f"⚠️  Não foi possível mapear faturamento: '{revenue_text}'")
    return None


def update_contact(contact_id: int, revenue_range: Optional[str] = None) -> None:
    """
    Updates a contact in Ploomes with revenue range.
    Revenue field is stored in the Contact, not the Deal.
    """
    if not revenue_range:
        return
    
    revenue_id = map_revenue_to_ploomes_id(revenue_range)
    if not revenue_id:
        print(f"⚠️  Não foi possível atualizar faturamento: mapeamento falhou para '{revenue_range}'")
        return
    
    # Try array format (like Deal updates)
    payload = {
        "OtherProperties": [
            {
                "FieldKey": "contact_F713F5E5-D54A-4CD1-A358-B266BE0719FA",
                "IntegerValue": revenue_id
            }
        ]
    }
    
    url = f"{PLOOMES_BASE_URL}/Contacts({contact_id})"
    response = requests.patch(url, json=payload, headers=get_headers(), timeout=10)
    
    if not response.ok:
        print(f"PLOOMES CONTACT UPDATE ERROR: {response.status_code} - {response.text}")
        response.raise_for_status()

from typing import Iterable, List, Tuple

import requests
from django.conf import settings

from .models import Vendor

def fetch_vendors_from_api(limit: int = 100) -> List[dict]:
    """
    Consulta a API externa de vendedores definida em settings.
    """
    base_url = settings.CEMAG_API_BASE_URL.rstrip("/")
    url = f"{base_url}/vendedores"
    headers = {"Authorization": f"Bearer {settings.CEMAG_API_TOKEN}"} if settings.CEMAG_API_TOKEN else {}
    response = requests.get(url, headers=headers, params={"limit": limit}, timeout=10)
    response.raise_for_status()
    payload = response.json()
    if isinstance(payload, dict) and "results" in payload:
        return payload["results"]
    if isinstance(payload, list):
        return payload
    return []

def sync_vendors(external_vendors: Iterable[dict]) -> Tuple[int, int]:
    """
    Persiste na base os vendedores retornados da API.
    Retorna uma tupla (criados, atualizados).
    """
    created_count = 0
    updated_count = 0
    for vendor in external_vendors:
        code = str(vendor.get("code") or vendor.get("id") or "").strip()
        if not code:
            continue

        defaults = {
            "name": vendor.get("name", ""),
            "email": vendor.get("email", ""),
            "region": vendor.get("region", ""),
            "phone": vendor.get("phone", ""),
            "is_active": vendor.get("is_active", True),
        }
        obj, created = Vendor.objects.update_or_create(code=code, defaults=defaults)
        created_count += int(created)
        updated_count += int(not created)
    return created_count, updated_count

def _zip_products_from_arrays(payload):
    """Aceita listas paralelas e monta uma lista de produtos normalizada."""
    required = ["listaProdutos", "listaCores", "listaPreco", "listaQuantidade"]
    if not all(k in payload for k in required):
        return []

    produtos = payload.get("listaProdutos") or []
    cores = payload.get("listaCores") or []
    precos = payload.get("listaPreco") or []
    quantidades = payload.get("listaQuantidade") or []
    preco_unit = payload.get("listaPrecoUnitario") or []
    descontos = payload.get("listaPercentDesconto") or []
    prazos = payload.get("listaPrazo") or []
    group_ids = payload.get("listaGroupId") or []

    items = []
    for idx, prod_id in enumerate(produtos):
        items.append(
            {
                "product_id": prod_id,
                "group_id": group_ids[idx] if idx < len(group_ids) else None,
                "prazo": prazos[idx] if idx < len(prazos) else None,
                "color_id": cores[idx] if idx < len(cores) else None,
                "price": precos[idx] if idx < len(precos) else 0,
                "quantity": quantidades[idx] if idx < len(quantidades) else 1,
                "unit_price": preco_unit[idx] if idx < len(preco_unit) else (precos[idx] if idx < len(precos) else 0),
                "discount": descontos[idx] if idx < len(descontos) else 0,
            }
        )
    return items

def get_prop_value(properties_list, field_key, value_type='IntegerValue'):
    """
    Busca um valor específico dentro de uma lista de propriedades baseado na FieldKey.
    Retorna None se não encontrar.
    """

    prop = next((p for p in properties_list if p.get('FieldKey') == field_key), None)
    
    if prop:
        return prop.get(value_type)
    return None
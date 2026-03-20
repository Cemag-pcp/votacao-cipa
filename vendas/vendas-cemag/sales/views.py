from django.contrib import messages
from django.contrib.auth.hashers import check_password
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from collections import defaultdict
import json
import requests
from django.conf import settings
from datetime import datetime, timedelta, date

from .models import (
    CartItem,
    FavoriteItem,
    PortalUser,
    PriceList,
    Vendor,
    FamilyPhoto,
    GrupoPrazo,
    ProdutoInnovaro,
    PrecoProduto,
    Cores,
    FormaPagamento,
)
from .services import fetch_vendors_from_api, sync_vendors, _zip_products_from_arrays, get_prop_value

@require_GET
def vendors(request):
    source = request.GET.get("source", "db")
    if source == "external":
        try:
            limit = int(request.GET.get("limit", 100))
        except ValueError:
            limit = 100
        try:
            data = fetch_vendors_from_api(limit=limit)
        except Exception as exc:  # pragma: no cover - simples log de erro
            return JsonResponse({"detail": f"Falha ao consultar API externa: {exc}"}, status=502)

        return JsonResponse({"source": "external_api", "count": len(data), "results": data})

    vendors_qs = Vendor.objects.all().values("code", "name", "email", "region", "phone", "is_active")
    data = list(vendors_qs)
    return JsonResponse({"source": "database", "count": len(data), "results": data})


@csrf_exempt  # endpoint pensado para integrações de serviço; ajuste se for expor publicamente
@require_POST
def sync(request):
    try:
        data = fetch_vendors_from_api(limit=int(request.POST.get("limit", 100)))
    except Exception as exc:  # pragma: no cover - simples log de erro
        return JsonResponse({"detail": f"Falha ao consultar API externa: {exc}"}, status=502)

    created, updated = sync_vendors(data)
    return JsonResponse(
        {"detail": "Sincronizado com sucesso", "created": created, "updated": updated, "total": created + updated}
    )


@require_GET
def home(request):
    if not request.session.get("owner_id"):
        return redirect("login")
    context = {
        "owner_id": request.session.get("owner_id"),
        "user_name": request.session.get("user_name"),
    }
    return render(request, "sales/home.html", context)


def login_view(request):
    if request.session.get("owner_id"):
        return redirect("home")

    if request.method == "POST":
        login = request.POST.get("login")
        password = request.POST.get("password")
        if not login or not password:
            messages.error(request, "Informe login e senha.")
            return redirect("login")

        try:
            user = PortalUser.objects.get(login=login)
        except PortalUser.DoesNotExist:
            messages.error(request, "Usuário não encontrado. Cadastre via admin.")
            return redirect("login")

        if not check_password(password, user.password):
            messages.error(request, "Senha inválida.")
            return redirect("login")

        profile_id = _resolve_profile_id_by_owner_id(user.owner_id)
        try:
            profile_id = int(profile_id) if profile_id is not None else None
        except (TypeError, ValueError):
            profile_id = None

        assigned_price_lists = list(user.price_lists.values_list("name", flat=True))
        if not assigned_price_lists and user.price_list:
            assigned_price_lists = [user.price_list]

        request.session["owner_id"] = user.owner_id
        request.session["user_name"] = user.name
        request.session["login"] = user.login
        request.session["price_list"] = assigned_price_lists[0] if assigned_price_lists else None
        request.session["price_lists"] = assigned_price_lists
        request.session["profile_id"] = profile_id
        return redirect("home")

    return render(request, "sales/login.html")


def logout_view(request):
    request.session.flush()
    return redirect("login")


def create_quote(request):
    if not request.session.get("owner_id"):
        return redirect("login")
    price_lists = request.session.get("price_lists") or []
    if not price_lists and request.session.get("price_list"):
        price_lists = [request.session.get("price_list")]
    context = {
        "owner_id": request.session.get("owner_id"),
        "user_name": request.session.get("user_name"),
        "price_list": price_lists[0] if price_lists else None,
        "price_lists": price_lists,
        "profile_id": request.session.get("profile_id"),
    }
    return render(request, "sales/create_quote.html", context)


@require_GET
def consult_price(request):
    """Tela de consulta de preços - usuário busca produtos e depois preenche dados do cliente"""
    if not request.session.get("owner_id"):
        return redirect("login")
    price_lists = request.session.get("price_lists") or []
    if not price_lists and request.session.get("price_list"):
        price_lists = [request.session.get("price_list")]
    context = {
        "owner_id": request.session.get("owner_id"),
        "user_name": request.session.get("user_name"),
        "price_list": price_lists[0] if price_lists else None,
        "price_lists": price_lists,
        "profile_id": request.session.get("profile_id"),
        "is_consult_mode": True,
    }
    return render(request, "sales/consult_price.html", context)


@csrf_exempt
@require_POST
def add_to_cart(request):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    try:
        item = CartItem.objects.create(
            owner_id=request.session.get("owner_id"),
            product_code=data.get("product_code", ""),
            description=data.get("description", ""),
            list_name=data.get("list_name", ""),
            color=data.get("color", ""),
            price=data.get("price", 0) or 0,
            discount_percent=data.get("discount_percent", 0) or 0,
            final_price=data.get("final_price", 0) or 0,
            favorite=bool(data.get("favorite", False)),
            quantity=int(data.get("quantity", 1) or 1),
        )
        return JsonResponse({"detail": "Item adicionado ao carrinho.", "id": item.id})
    except Exception as exc:
        return JsonResponse({"detail": f"Erro ao adicionar: {exc}"}, status=500)


@csrf_exempt
@require_GET
def list_cart(request):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    items = CartItem.objects.filter(owner_id=request.session.get("owner_id")).order_by("-created_at")
    data = [
        {
            "id": item.id,
            "product_code": item.product_code,
            "description": item.description,
            "list_name": item.list_name,
            "color": item.color,
            "price": float(item.price),
            "discount_percent": float(item.discount_percent),
            "final_price": float(item.final_price),
            "favorite": item.favorite,
            "quantity": item.quantity,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]
    return JsonResponse({"items": data})


@csrf_exempt
@require_POST
def update_cart_item(request, item_id):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    try:
        item = CartItem.objects.get(id=item_id, owner_id=request.session.get("owner_id"))
    except CartItem.DoesNotExist:
        return JsonResponse({"detail": "Item não encontrado."}, status=404)

    for field in ["color", "description", "list_name"]:
        if field in data:
            setattr(item, field, data[field] or "")
    if "price" in data:
        item.price = data["price"] or 0
    if "discount_percent" in data:
        item.discount_percent = data["discount_percent"] or 0
    if "final_price" in data:
        item.final_price = data["final_price"] or 0
    if "favorite" in data:
        item.favorite = bool(data["favorite"])
    if "quantity" in data:
        try:
            item.quantity = max(1, int(data["quantity"]))
        except (TypeError, ValueError):
            pass

    item.save()
    return JsonResponse({"detail": "Item atualizado."})


@csrf_exempt
@require_POST
def delete_cart_item(request, item_id):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        item = CartItem.objects.get(id=item_id, owner_id=request.session.get("owner_id"))
    except CartItem.DoesNotExist:
        return JsonResponse({"detail": "Item não encontrado."}, status=404)
    item.delete()
    return JsonResponse({"detail": "Item removido."})


@csrf_exempt
@require_POST
def clear_cart(request):
    """Remove todos os itens do carrinho do usuário logado (owner_id)."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    CartItem.objects.filter(owner_id=request.session.get("owner_id")).delete()
    return JsonResponse({"detail": "Carrinho limpo."})


def _ploomes_headers():
    token = getattr(settings, "CEMAG_API_TOKEN", "")
    return {"User-Key": token, "Content-Type": "application/json"}


PRICE_LIST_OPTIONS = [
    "Lista Preço SDE e COE",
    "Lista Preço MT",
    "Lista Preço N e NE",
]


def _resolve_profile_id_by_owner_id(owner_id):
    """Busca o ProfileId do usuario no Ploomes pelo OwnerId."""
    if not owner_id:
        return None

    try:
        resp = requests.get("https://api2.ploomes.com/Users", headers=_ploomes_headers(), timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    data = resp.json()
    users = data.get("value", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    for user in users:
        user_id = user.get("id") or user.get("Id") or user.get("ID")
        if user_id == owner_id:
            return user.get("profileid") or user.get("ProfileId") or user.get("profileId")
    return None


def _add_business_days(start_date: date, business_days: int) -> date:
    """Soma dias uteis (ignora sabado e domingo)."""
    current = start_date
    added = 0
    while added < business_days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


def _delivery_deadline_payload():
    """
    Calcula prazos de entrega.
    Regra atual (fallback local): base em hoje, com minimos corridos.
    """
    hoje = date.today()

    # Regra base em dias uteis
    prazo_carga_fechada = _add_business_days(hoje, 5)
    prazo_carreta_avulsa = _add_business_days(hoje, 15)

    dias_corridos_fechada = (prazo_carga_fechada - hoje).days
    dias_corridos_avulsa = (prazo_carreta_avulsa - hoje).days

    # Minimos corridos
    min_fechada = 25
    min_avulsa = 35

    if dias_corridos_fechada < min_fechada:
        prazo_carga_fechada = hoje + timedelta(days=min_fechada)
        dias_corridos_fechada = min_fechada

    if dias_corridos_avulsa < min_avulsa:
        prazo_carreta_avulsa = hoje + timedelta(days=min_avulsa)
        dias_corridos_avulsa = min_avulsa

    return {
        "prazo_carreta_avulsa": prazo_carreta_avulsa.isoformat(),
        "prazo_carga_fechada": prazo_carga_fechada.isoformat(),
        "dias_corridos_fechada": dias_corridos_fechada,
        "dias_corridos_avulsa": dias_corridos_avulsa,
    }


@require_GET
def prazo_entrega(request):
    """API para calcular prazo de entrega para exibicao no painel."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    try:
        payload = _delivery_deadline_payload()
        return JsonResponse(payload)
    except Exception as exc:
        return JsonResponse({"detail": f"Falha ao calcular prazo de entrega: {exc}"}, status=500)

def _resolve_owner_id_by_name(name):
    """Busca o Id do usuario Ploomes pelo nome (case-insensitive)."""
    normalized = (name or "").strip().lower()
    if not normalized:
        return None

    try:
        resp = requests.get("https://api2.ploomes.com/Users", headers=_ploomes_headers(), timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException:
        return None

    data = resp.json()
    users = data.get("value", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    for user in users:
        user_name = (
            user.get("name")
            or user.get("Name")
            or user.get("NAME")
            or ""
        ).strip().lower()
        user_id = user.get("id") or user.get("Id") or user.get("ID")
        if user_name == normalized and user_id:
            return user_id
    return None


def _resolve_city_payload(city_name):
    """
    Consulta a cidade no Ploomes e retorna um dict:
    {"city_id": int, "state_name": str, "city_name": str}
    """
    city_name = (city_name or "").strip()
    if not city_name:
        return None

    safe_name = city_name.replace("'", "''")
    params = {
        "$top": 20,
        "$expand": "Country,State",
        "$filter": f"Name eq '{safe_name}'",
    }
    try:
        resp = requests.get(
            "https://public-api2.ploomes.com/Cities",
            headers=_ploomes_headers(),
            params=params,
            timeout=15,
        )
    except requests.exceptions.RequestException:
        return None

    if not resp.ok:
        return None

    payload = resp.json() if resp.content else {}
    values = payload.get("value") or []
    if not values:
        return None

    city = values[0] or {}
    state = city.get("State") or {}
    return {
        "city_id": city.get("Id"),
        "state_name": state.get("Name") or state.get("Short") or "",
        "city_name": city.get("Name") or city_name,
    }


def _search_cities_payload(term="", top=20):
    """Lista cidades no Ploomes para autocomplete."""
    term = (term or "").strip()
    try:
        top = max(1, min(int(top), 50))
    except (TypeError, ValueError):
        top = 20

    params = {
        "$top": top,
        "$select": "Id,Name",
        "$expand": "State($select=Name,Short)",
        "$orderby": "Name asc",
    }
    if term:
        safe_term = term.replace("'", "''")
        params["$filter"] = f"contains(Name,'{safe_term}')"

    try:
        resp = requests.get(
            "https://public-api2.ploomes.com/Cities",
            headers=_ploomes_headers(),
            params=params,
            timeout=15,
        )
    except requests.exceptions.RequestException:
        return []

    if not resp.ok:
        return []

    payload = resp.json() if resp.content else {}
    values = payload.get("value") or []
    results = []
    for item in values:
        state = item.get("State") or {}
        results.append(
            {
                "id": item.get("Id"),
                "cidade": item.get("Name") or "",
                "estado": state.get("Name") or state.get("Short") or "",
            }
        )
    return results


def _search_companies_payload(owner_id, term="", top=100):
    """Lista empresas (TypeId=1) do Ploomes para autocomplete."""
    if not owner_id:
        return []

    term = (term or "").strip()
    try:
        top = max(1, min(int(top), 100))
    except (TypeError, ValueError):
        top = 100

    safe_term = term.replace("'", "''")
    filter_parts = [f"OwnerId eq {owner_id}", "TypeId eq 1"]
    if safe_term:
        filter_parts.insert(0, f"contains(Name,'{safe_term}')")

    params = {
        "$top": top,
        "$select": "Name,Id",
        "$orderby": "Name asc",
        "$filter": " and ".join(filter_parts),
    }
    try:
        resp = requests.get(
            "https://public-api2.ploomes.com/Contacts",
            headers=_ploomes_headers(),
            params=params,
            timeout=15,
        )
    except requests.exceptions.RequestException:
        return []

    if not resp.ok:
        return []

    payload = resp.json() if resp.content else {}
    values = payload.get("value") or []
    return [{"id": item.get("Id"), "nome": item.get("Name") or ""} for item in values if item]


def _resolve_phone_type_code(payload):
    """Resolve o codigo do tipo de telefone; aceita inteiro ou texto."""
    code = payload.get("codigoTipoTelefone")
    if code not in (None, ""):
        try:
            return int(code)
        except (TypeError, ValueError):
            pass

    phone_type = (payload.get("tipoTelefone") or "").strip().lower()
    # Fallback simples para os tipos mais comuns.
    mapping = {
        "comercial": 1,
        "celular": 1,
        "residencial": 1,
        "whatsapp": 1,
    }
    return mapping.get(phone_type, 1)


@require_GET
def ploomes_validate_city(request):
    """Valida cidade via Ploomes e retorna Id/estado para uso no cadastro."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    city_name = request.GET.get("cidade", "")
    city_payload = _resolve_city_payload(city_name)
    if not city_payload or not city_payload.get("city_id"):
        return JsonResponse({"detail": "Cidade nao encontrada."}, status=404)

    return JsonResponse(
        {
            "valid": True,
            "cidade": city_payload["city_name"],
            "estado": city_payload["state_name"],
            "cidade_id": city_payload["city_id"],
        }
    )


@require_GET
def ploomes_cities_search(request):
    """Retorna sugestoes de cidades para o campo de autocomplete."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    term = request.GET.get("term", "")
    top = request.GET.get("top", 20)
    results = _search_cities_payload(term=term, top=top)
    return JsonResponse({"results": results, "count": len(results)})


@csrf_exempt
@require_POST
def ploomes_create_company(request):
    """
    Cria uma empresa (contact TypeId=1) no Ploomes.
    Campos esperados:
    nome, cnpj, telefone, tipoTelefone, cidade, responsavel, condicao, tipo_id
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload invalido."}, status=400)

    nome = (data.get("nome") or "").strip()
    cnpj = (data.get("cnpj") or "").strip()
    telefone = (data.get("telefone") or "").strip()
    tipo_telefone = (data.get("tipoTelefone") or "").strip() or "Comercial"
    cidade = (data.get("cidade") or "").strip()
    responsavel = (data.get("responsavel") or "").strip()
    condicao = (data.get("condicao") or "").strip()
    tipo_id = data.get("tipo_id") or 1
    payload_owner_id = data.get("owner_id")

    if not nome or not cnpj or not telefone or not cidade:
        return JsonResponse({"detail": "nome, cnpj, telefone e cidade sao obrigatorios."}, status=400)

    try:
        tipo_id = int(tipo_id)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "tipo_id invalido."}, status=400)

    city_payload = _resolve_city_payload(cidade)
    if not city_payload or not city_payload.get("city_id"):
        return JsonResponse({"detail": "Cidade nao encontrada na base da Ploomes."}, status=400)

    owner_id = None
    if payload_owner_id not in (None, ""):
        try:
            owner_id = int(payload_owner_id)
        except (TypeError, ValueError):
            owner_id = None
    if not owner_id and responsavel:
        owner_id = _resolve_owner_id_by_name(responsavel)
    if not owner_id:
        owner_id = request.session.get("owner_id")

    codigo_tipo_telefone = _resolve_phone_type_code(data)
    contato = {
        "Name": nome,
        "Phones": [
            {
                "Type": {
                    "Id": codigo_tipo_telefone,
                    "Name": tipo_telefone,
                },
                "TypeId": codigo_tipo_telefone,
                "PhoneNumber": telefone,
                "Country": {
                    "Id": 76,
                    "Short": "BRA",
                    "Short2": "BR",
                    "Name": "BRASIL",
                    "PhoneMask": "(99) 9999?9-9999",
                },
                "CountryId": 76,
            }
        ],
        "CityId": city_payload["city_id"],
        "State": city_payload["state_name"],
        "Register": cnpj,
        "Country": "Brasil",
        "TypeId": tipo_id,
        "OwnerId": owner_id,
    }

    try:
        resp = requests.post(
            "https://public-api2.ploomes.com/Contacts?select=Id",
            headers=_ploomes_headers(),
            json=contato,
            timeout=20,
        )
    except requests.exceptions.RequestException as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if not resp.ok:
        return JsonResponse({"detail": "Falha ao criar empresa.", "response": resp.text}, status=resp.status_code)

    data_json = resp.json() if resp.content else {}
    values = data_json.get("value", []) if isinstance(data_json, dict) else []
    company_id = None
    if values and isinstance(values[0], dict):
        company_id = values[0].get("Id")
    if not company_id and isinstance(data_json, dict):
        company_id = data_json.get("Id")

    return JsonResponse(
        {
            "detail": "Empresa criada com sucesso.",
            "id": company_id,
            "cidade_id": city_payload["city_id"],
            "estado": city_payload["state_name"],
            "condicao": condicao,
        }
    )


@require_GET
def ploomes_companies_search(request):
    """Retorna sugestoes de empresas (Contacts TypeId=1) para autocomplete."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    term = request.GET.get("term", "")
    top = request.GET.get("top", 100)
    owner_id = request.GET.get("owner_id") or request.session.get("owner_id")
    results = _search_companies_payload(owner_id=owner_id, term=term, top=top)
    return JsonResponse({"results": results, "count": len(results)})


@csrf_exempt
@require_POST
def ploomes_create_contact(request):
    """
    Cria um contato (TypeId=2) vinculado a uma empresa no Ploomes.
    Campos esperados:
    company_id, nome, telefone, tipoTelefone, codigoTipoTelefone, cidade_id, cidade, owner_id
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload invalido."}, status=400)

    company_id = data.get("company_id")
    nome = (data.get("nome") or "").strip()
    telefone = (data.get("telefone") or "").strip()
    tipo_telefone = (data.get("tipoTelefone") or "").strip() or "Comercial"
    cidade_id = data.get("cidade_id")
    cidade_nome = (data.get("cidade") or "").strip()
    payload_owner_id = data.get("owner_id")

    if not company_id or not nome or not telefone:
        return JsonResponse({"detail": "company_id, nome e telefone sao obrigatorios."}, status=400)

    city_payload = None
    if cidade_id not in (None, ""):
        try:
            cidade_id = int(cidade_id)
        except (TypeError, ValueError):
            cidade_id = None

    if not cidade_id and cidade_nome:
        city_payload = _resolve_city_payload(cidade_nome)
        if city_payload and city_payload.get("city_id"):
            cidade_id = city_payload["city_id"]

    if not cidade_id:
        return JsonResponse({"detail": "Informe uma cidade valida."}, status=400)

    owner_id = None
    if payload_owner_id not in (None, ""):
        try:
            owner_id = int(payload_owner_id)
        except (TypeError, ValueError):
            owner_id = None
    if not owner_id:
        owner_id = request.session.get("owner_id")

    if city_payload is None:
        city_payload = _resolve_city_payload(cidade_nome) if cidade_nome else None
    estado = (city_payload or {}).get("state_name", "")

    codigo_tipo_telefone = _resolve_phone_type_code(data)
    contato = {
        "Name": nome,
        "Phones": [
            {
                "Type": {"Id": codigo_tipo_telefone, "Name": tipo_telefone},
                "TypeId": codigo_tipo_telefone,
                "PhoneNumber": telefone,
                "Country": {
                    "Id": 76,
                    "Short": "BRA",
                    "Short2": "BR",
                    "Name": "BRASIL",
                    "PhoneMask": "(99) 9999?9-9999",
                },
                "CountryId": 76,
            }
        ],
        "CompanyId": int(company_id),
        "Companies": [{"CompanyId": int(company_id)}],
        "CityId": int(cidade_id),
        "State": estado,
        "Country": "Brasil",
        "TypeId": 2,
        "OwnerId": owner_id,
    }

    try:
        resp = requests.post(
            "https://public-api2.ploomes.com/Contacts?select=Id",
            headers=_ploomes_headers(),
            json=contato,
            timeout=20,
        )
    except requests.exceptions.RequestException as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if not resp.ok:
        return JsonResponse({"detail": "Falha ao criar contato.", "response": resp.text}, status=resp.status_code)

    data_json = resp.json() if resp.content else {}
    values = data_json.get("value", []) if isinstance(data_json, dict) else []
    contact_id = None
    if values and isinstance(values[0], dict):
        contact_id = values[0].get("Id")
    if not contact_id and isinstance(data_json, dict):
        contact_id = data_json.get("Id")

    return JsonResponse({"detail": "Contato criado com sucesso.", "id": contact_id})


@require_GET
def ploomes_loss_reasons(request):
    """Lista motivos de perda (LossReasons) para um Pipeline.

    Query params:
    - pipeline_id: Id do pipeline (default: 37808)
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)

    pipeline_id = request.GET.get("pipeline_id", "37808")
    url = (
        f"https://public-api2.ploomes.com/Deals@LossReasons"
        f"?$filter=PipelineId+eq+{pipeline_id}&$select=Id,Name"
    )
    try:
        resp = requests.get(url, headers=_ploomes_headers(), timeout=15)
    except Exception as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if resp.status_code != 200:
        return JsonResponse({"detail": "Erro ao buscar motivos de perda", "response": resp.text}, status=resp.status_code)

    data = resp.json()
    # Normaliza saída
    values = data.get("value") or data.get("Values") or []
    reasons = [{"Id": r.get("Id"), "Name": r.get("Name")} for r in values]
    return JsonResponse({"data": reasons})


@require_GET
def ploomes_order_mirror(request):
    """Retorna a URL do espelho (DocumentUrl) da última ordem ligada ao Deal."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)

    deal_id = request.GET.get("deal_id") or request.GET.get("DealId")
    if not deal_id:
        return JsonResponse({"detail": "Informe deal_id."}, status=400)

    params = {
        "$filter": f"DealId eq {deal_id}",
        "$orderby": "CreateDate desc",
        "$top": 1,
        "$select": "Id,DocumentUrl,CreateDate",
    }
    try:
        resp = requests.get("https://public-api2.ploomes.com/Orders", headers=_ploomes_headers(), params=params, timeout=15)
    except Exception as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if resp.status_code != 200:
        return JsonResponse({"detail": "Erro ao buscar ordem do deal", "response": resp.text}, status=resp.status_code)

    data = resp.json()
    values = data.get("value") or []
    if not values:
        return JsonResponse({"detail": "Nenhuma ordem encontrada para este deal."}, status=404)

    doc_url = values[0].get("DocumentUrl")
    if not doc_url:
        return JsonResponse({"detail": "URL do documento não encontrada."}, status=404)

    return JsonResponse({"document_url": doc_url})


def _get_data_hoje_formato():
    """Retorna a data de hoje no formato ISO 8601 (YYYY-MM-DDTHH:MM:SS)."""
    return datetime.now().isoformat()


def _get_prazo_dias(dias=45):
    """Retorna a data de hoje + N dias no formato ISO 8601."""
    data_futura = datetime.now() + timedelta(days=dias)
    return data_futura.isoformat()


def _criar_venda_from_quote(deal_id, quote_id):
    """
    Função para criar uma venda (Order) no Ploomes após ganhar a proposta.
    
    Args:
        deal_id: ID do negócio (Deal)
        quote_id: ID da última proposta (Quote)
    
    Returns:
        dict com resultado da operação
    """
    headers = _ploomes_headers()
    
    # Step 1: Buscar a proposta completa com produtos
    try:
        url_quote = f"https://public-api2.ploomes.com/Quotes?$filter=DealId+eq+{deal_id}&$expand=Products($expand=OtherProperties)"
        resp_quote = requests.get(url_quote, headers=headers, timeout=15)
        
        if resp_quote.status_code != 200:
            return {
                "success": False,
                "detail": f"Erro ao buscar proposta: {resp_quote.status_code}",
                "response": resp_quote.text
            }
        
        data = resp_quote.json()
        if not data.get("value") or len(data["value"]) == 0:
            return {
                "success": False,
                "detail": "Nenhuma proposta encontrada para este deal"
            }
        
        quote_data = data["value"][0]
        
        owner_id = quote_data.get("OwnerId")
        person_id = quote_data.get("PersonId")
        contact_id = quote_data.get("ContactId")
        amount = quote_data.get("Amount", 0)
        notes = quote_data.get("Notes", "")
        json_produtos = quote_data.get("Products", [])
        
    except Exception as exc:
        return {
            "success": False,
            "detail": f"Erro ao buscar proposta: {exc}"
        }
    
    # Step 2: Montar o JSON da venda
    json_order = {
        "ContactId": contact_id,
        "DealId": deal_id,
        "PersonId": person_id,
        "OwnerId": owner_id,
        "CurrencyId": 1,
        "Amount": amount,
        "OriginQuoteId": quote_id,
        "OtherProperties": [
            {
                "FieldKey": "order_7BB4AC64-8B0F-40AF-A854-CBE860A4B179",  # Observação
                "BigStringValue": notes
            },
            {
                "FieldKey": "order_2A8B87D1-3E73-4C5A-94F5-29A53347FFC1",  # Atualizar dados
                "BoolValue": True
            },
            {
                "FieldKey": "order_62D206E8-1881-4234-A341-F9E82C08885C",  # Programação de entrega
                "DateTimeValue": _get_prazo_dias(45)
            },
            {
                "FieldKey": "order_7932F9F0-B3E8-40D3-9815-53C8613D33F1",  # Valor Total
                "DecimalValue": amount
            },
            {
                "FieldKey": "order_377A29A2-69F9-4E34-9307-0764EE3D9A89",  # Prazo Dias
                "IntegerValue": 45
            }
        ],
        "Date": _get_data_hoje_formato(),
        "Sections": [{"Products": [], "Total": amount}],
    }
    
    # Step 3: Processar produtos
    for product_item in json_produtos:
        # Buscar o valor do desconto nos OtherProperties
        discount_value = None
        for other_prop in product_item.get("OtherProperties", []):
            if other_prop.get("FieldKey") == "quote_product_7FD5E293-CBB5-43C8-8ABF-B9611317DF75":
                discount_value = other_prop.get("DecimalValue")
                break
        
        # Montar o produto para a ordem
        quantity = product_item.get("Quantity", 1)
        total = product_item.get("Total", 0)
        unit_price = total / quantity if quantity > 0 else 0
        
        new_product = {
            "OtherProperties": [
                {
                    "FieldKey": "order_table_product_69BAEC44-676C-4458-823A-C0F29E605B0F",  # Valor unitário com desconto
                    "DecimalValue": unit_price
                },
                {
                    "FieldKey": "order_table_product_56BC6561-A0C8-4EA7-BF03-40ADC8D03899",  # Previsão de Entrega
                    "DateTimeValue": _get_prazo_dias(45)
                }
            ],
            "Quantity": quantity,
            "UnitPrice": unit_price,
            "Total": total,
            "ProductId": product_item.get("ProductId"),
            "Discount": discount_value
        }
        
        json_order["Sections"][0]["Products"].append(new_product)
    
    # Step 4: Criar a ordem no Ploomes
    try:
        url_order = "https://public-api2.ploomes.com/Orders"
        resp_order = requests.post(url_order, headers=headers, json=json_order, timeout=20)
        
        if resp_order.status_code not in (200, 201):
            return {
                "success": False,
                "detail": f"Erro ao criar venda: {resp_order.status_code}",
                "response": resp_order.text
            }
        
        order_response = resp_order.json() if resp_order.content else {}
        order_id = order_response.get("Id")
        
        return {
            "success": True,
            "detail": "Venda criada com sucesso",
            "order_id": order_id,
            "deal_id": deal_id
        }
        
    except Exception as exc:
        return {
            "success": False,
            "detail": f"Erro ao criar venda: {exc}"
        }


@require_GET
def ploomes_payment_id(request):
    """Retorna ids/descrições de formas de pagamento (busca local).

    Mantém o mesmo formato do Ploomes (Id/Name/TableId), porém lendo da tabela
    local `sales.FormaPagamento` (sincronizada via rotina routines/sync_forma_pagamento).
    """
    try:
        rows = (
            FormaPagamento.objects.all()
            .values("pagamento_id", "descricao", "table_id")
            .order_by("descricao")
        )
        data = [
            {"Id": r["pagamento_id"], "Name": r["descricao"], "TableId": r["table_id"]}
            for r in rows
        ]
    except Exception as exc:
        return JsonResponse({"detail": f"Erro ao consultar forma de pagamento no banco: {exc}"}, status=500)

    if not data:
        return JsonResponse(
            {
                "detail": "Nenhuma opção encontrada no banco. Execute a rotina de sincronização de formas de pagamento.",
            },
            status=404,
        )

    return JsonResponse({"data": data})

@require_GET
def ploomes_color_id(request):
    """Retorna o Id da cor pelo nome (busca local).

    Este endpoint existia para evitar expor o User-Key no frontend.
    Agora ele consulta a tabela local `sales.Cores` (sincronizada via rotina routines/sync_cores).
    """
    color_name = (request.GET.get("color") or request.GET.get("nome") or "").strip()
    if not color_name:
        return JsonResponse({"detail": "Parâmetro 'color' é obrigatório."}, status=400)

    try:
        # Suporte opcional: se vier um ID numérico, tenta buscar direto.
        if color_name.isdigit():
            cor = Cores.objects.filter(cor_id=int(color_name)).first()
        else:
            cor = Cores.objects.filter(descricao__iexact=color_name).first()
    except Exception as exc:
        return JsonResponse({"detail": f"Erro ao consultar cor no banco: {exc}"}, status=500)

    if not cor:
        return JsonResponse(
            {
                "detail": "Cor não encontrada no banco. Execute a rotina de sincronização de cores.",
                "nome": color_name,
            },
            status=404,
        )

    return JsonResponse({"id": cor.cor_id, "nome": cor.descricao})


@require_GET
def ploomes_product_id(request):
    """Retorna o Id e GroupId do produto pelo código."""
    code = request.GET.get("code") or request.GET.get("product_code") or ""
    if not code:
        return JsonResponse({"detail": "Parâmetro 'code' é obrigatório."}, status=400)
    url = (
        "https://public-api2.ploomes.com/Products"
        "?$top=1&$filter=Code+eq+'{}'&$select=Id,GroupId,Code"
    ).format(code)
    try:
        resp = requests.get(url, headers=_ploomes_headers(), timeout=10)
        if not resp.ok:
            return JsonResponse({"detail": "Produto não encontrado."}, status=resp.status_code)
        data = resp.json().get("value") or []
        if not data:
            return JsonResponse({"detail": "Produto não encontrado."}, status=404)
        prod = data[0]
        return JsonResponse({"id": prod.get("Id"), "group_id": prod.get("GroupId"), "code": prod.get("Code")})
    except Exception as exc:
        return JsonResponse({"detail": f"Erro ao consultar produto: {exc}"}, status=502)


@require_GET
def ploomes_quotes(request):
    owner_id = request.GET.get("owner_id")
    if not owner_id:
        return JsonResponse({"results": []}, status=400)
    top = request.GET.get("top", 20)
    skip = request.GET.get("skip", 0)
    status_filter = request.GET.get("status")
    if status_filter in (None, "", "undefined", "null"):
        status_filter = "1"  # padrão: Em aberto
    aceite = request.GET.get("aceite")
    aprovacao = request.GET.get("aprovacao")
    revenda = request.GET.get("revenda")

    base_filter = f"OwnerId eq {owner_id} and LastReview eq true"
    if status_filter and status_filter != "outros":
        base_filter += f" and Deal/StatusId eq {status_filter}"
    elif status_filter == "outros":
        base_filter += " and Deal/StatusId not in (1,2,3)"
    if aceite:
        base_filter += f" and ExternallyAccepted eq {aceite}"
    if aprovacao:
        base_filter += f" and ApprovalStatusId eq {aprovacao}"
    if revenda:
        base_filter += f" and contains(ContactName,'{revenda}')"

    params = {
        "$expand": "Installments,Products($select=Id),Approvals($select=Id),ExternalComments($select=Id),Comments($select=Id),Deal",
        "preload": "true",
        "$orderby": "CreateDate desc",
        "$top": top,
        "$skip": skip,
        "$filter": base_filter,
    }

    resp = requests.get("https://public-api2.ploomes.com/Quotes", params=params, headers=_ploomes_headers(), timeout=15)
    
    return JsonResponse(resp.json(), status=resp.status_code)


@require_GET
def ploomes_contacts_search(request):
    term = request.GET.get("term", "")
    owner = request.GET.get("owner", "")
    try:
        top = int(request.GET.get("top", 30))
    except (TypeError, ValueError):
        top = 30
    top = max(1, min(top, 100))

    # Se não tiver termo ou dono, retorna vazio
    if not term or not owner:
        return JsonResponse({"results": []})

    params = {
        "$top": top,
        "$select": "Name,Id",
        "$filter": f"contains(Name,'{term}') and OwnerId eq {owner}",
        "$expand": "City($select=Id,Name;$expand=State($select=Short,Name))"
    }

    resp = requests.get(
        "https://public-api2.ploomes.com/Contacts", 
        params=params, 
        headers=_ploomes_headers(), 
        timeout=10
    )
    
    return JsonResponse({"results": resp.json().get("value", [])}, status=resp.status_code)

@require_GET
def ploomes_contacts_company(request):
    company_id = request.GET.get("company_id")
    owner = request.GET.get("owner", "")
    if not company_id:
        return JsonResponse({"results": []})
    params = {
        "$top": 100,
        "$select": "Name,Id",
        "$filter": f"CompanyId eq {company_id} and TypeId eq 2 and OwnerId eq {owner}",
    }
    resp = requests.get("https://public-api2.ploomes.com/Contacts", params=params, headers=_ploomes_headers(), timeout=10)
    return JsonResponse({"results": resp.json().get("value", [])}, status=resp.status_code)


@require_GET
def ploomes_quote_detail(request):
    quote_id = request.GET.get("quote_id")
    if not quote_id:
        return JsonResponse({"detail": "quote_id é obrigatório"}, status=400)

    params = {
        "$filter": f"Id eq {quote_id}",
        "$select": "Id,ContactName,ContactId,DealId,PersonId,PersonName,Key,Notes",
        "$expand": "OtherProperties,Products($expand=OtherProperties($filter=FieldKey eq 'quote_product_76A1F57A-B40F-4C4E-B412-44361EB118D8';$select=FieldKey,ObjectValueName,IntegerValue),Product($expand=OtherProperties))",
    }

    resp = requests.get(f"https://public-api2.ploomes.com/Quotes", params=params, headers=_ploomes_headers(), timeout=15)
    if not resp.ok:
        return JsonResponse({"detail": "Erro ao consultar proposta", "response": resp.text}, status=resp.status_code)

    data = resp.json() if resp.content else {}

    quote_data = data.get("value", [{}])[0]
    quote_other_props = quote_data.get("OtherProperties") or []

    products = []
    for p in quote_data.get("Products") or []:
        prod_info = p.get("Product") or {}
        
        target_field_key = 'quote_product_76A1F57A-B40F-4C4E-B412-44361EB118D8'
        color_id = None

        # Obtemos a lista de propriedades extras do ITEM DA PROPOSTA (não do produto base)
        other_props_item = p.get("OtherProperties") or []
        
        for prop in other_props_item:
            if prop.get('FieldKey') == target_field_key:
                color_id = prop.get('IntegerValue')
                break
        # ---------------------------------------------

        products.append(
            {
                "product_id": prod_info.get("Id"),
                "product_code": prod_info.get("Code"),
                "description": prod_info.get("Name"),
                "quantity": p.get("Quantity") if p.get("Quantity") is not None else 1,
                "unit_price": p.get("Total") / p.get("Quantity"),
                "total": p.get("Total") or 0,
                "discount_percent": float(p.get("Discount"))/100 or 0 if p.get("Discount") is not None else 0,
                "color_id": color_id, 
                "original_price": p.get("UnitPrice")
,
            }
        )

    payload = {
        "quote": {
            # Acessamos os dados principais também do dicionário correto
            "Id": quote_data.get("Id"),
            "DealId": quote_data.get("DealId"),
            "ContactName": quote_data.get("ContactName"),
            "ContactId": quote_data.get("ContactId"),
            "PersonId": quote_data.get("PersonId"),
            "PersonName": quote_data.get("PersonName"),
            "Key": quote_data.get("Key"),
            "Notes": quote_data.get("Notes"),
            "PaymentId": get_prop_value(quote_other_props, 'quote_E85539A9-D0D3-488E-86C5-66A49EAF5F3A', 'IntegerValue'), # quote_E85539A9-D0D3-488E-86C5-66A49EAF5F3A | IntegerValue
            "PaymentName": get_prop_value(quote_other_props, 'quote_DE50A0F4-1FBE-46AA-9B5D-E182533E4B4A', 'StringValue'), # quote_DE50A0F4-1FBE-46AA-9B5D-E182533E4B4A | StringValue
            "PaymentId2": get_prop_value(quote_other_props, 'quote_0FB9F0CB-2619-44C5-92BD-1A2D2D818BFE', 'IntegerValue'), # quote_0FB9F0CB-2619-44C5-92BD-1A2D2D818BFE | IntegerValue
        },
        "products": products,
    }

    print(products)

    return JsonResponse(payload)

@require_GET
def ploomes_quote_info(request):
    """Busca infos de uma proposta para revisão/edição."""
    quote_id = request.GET.get("quote_id") or request.GET.get("id")
    if not quote_id:
        return JsonResponse({"detail": "quote_id é obrigatório"}, status=400)

    url = (
        "https://public-api2.ploomes.com/Quotes"
        f"?$filter=true and Id eq {quote_id}"
        "&$expand=OtherProperties,Contact,"
        "Deal($select=Id,Title,Status;$expand=Status($select=Id,Name)),"
        "Creator($select=Id,Name,AvatarUrl)"
    )

    try:
        resp = requests.get(url, headers=_ploomes_headers(), timeout=15)
    except Exception as exc:  # pragma: no cover - integração externa
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if not resp.ok:
        return JsonResponse({"detail": "Erro ao buscar proposta", "response": resp.text}, status=resp.status_code)

    data = resp.json() or {}
    values = data.get("value") or []
    if not values:
        return JsonResponse({"detail": "Proposta não encontrada."}, status=404)

    q = values[0]
    other_props = q.get("OtherProperties") or []
    payment_prop = next(
        (
            p
            for p in other_props
            if p.get("FieldKey") == "quote_0FB9F0CB-2619-44C5-92BD-1A2D2D818BFE"
        ),
        {},
    )

    payload = {
        "nomeEmpresa": q.get("ContactName"),
        "idEmpresa": q.get("ContactId"),
        "nomeContato": q.get("PersonName"),
        "idContato": q.get("PersonId"),
        "formaPagamento": payment_prop.get("ObjectValueName"),
        "idFormaPagamento": payment_prop.get("Id"),
        "observacao": q.get("Notes"),
    }
    return JsonResponse(payload)


@require_GET
def ploomes_payment_options(request):
    contact_id = request.GET.get("contact_id")
    if not contact_id:
        return JsonResponse({"results": []})
    params = {
        "$top": 1,
        "$select": "Name",
        "$expand": "OtherProperties",
        "$filter": f"Id eq {contact_id}",
    }
    resp = requests.get("https://public-api2.ploomes.com/Contacts", params=params, headers=_ploomes_headers(), timeout=10)
    return JsonResponse({"results": resp.json().get("value", [])}, status=resp.status_code)


@csrf_exempt
@require_POST
def ploomes_create_quote(request):
    """Cria uma proposta (Quote) no Ploomes a partir de um Deal e itens."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    deal_id = payload.get("DealId") or payload.get("deal_id")
    forma_pagamento = payload.get("PaymentId")
    forma_pagamento_name = payload.get("paymentName")
    forma_pagamento_id_tipo2 = payload.get("PaymentIdTipo2")
    observacao = payload.get("observacao") or payload.get("notes") or ""
    owner_id = payload.get("OwnerId") or payload.get("owner_id") or request.session.get("owner_id")
    uf = (payload.get("uf") or "").strip().upper()

    if uf:
        if uf == 'CE':
            tipo_frete = 57972827
        else:
            tipo_frete = 22886508
    else:
        tipo_frete = 22886508

    products_payload = payload.get("products") or _zip_products_from_arrays(payload)

    if not deal_id or not products_payload:
        return JsonResponse({"detail": "Informe DealId e pelo menos um produto."}, status=400)

    total = 0
    total_itens = 0
    max_prazo = 0
    products = []

    for idx, product in enumerate(products_payload):
        qty = max(1, int(product.get("quantity", 1) or 1))
        line_total = float(product.get("total", 0) or 0)
        unit_price = float(product.get("unit_price", 0) or 0) or (line_total / qty if qty else 0)
        discount = float(product.get("discount_percent", 0) or 0)
        prazo = product.get("prazo") or 0
        try:
            group_id = product.get("group_id") or product.get("groupId") or product.get("GroupId")
            if group_id:
                gp = GrupoPrazo.objects.filter(grupo_code=str(group_id)).first()
                if gp and gp.prazo is not None:
                    prazo = gp.prazo
        except Exception:
            pass
        max_prazo = max(max_prazo, prazo or 0)

        total += line_total
        total_itens += qty

        products.append(
            {
                "Quantity": qty,
                "UnitPrice": unit_price,
                "Total": line_total,
                "ProductId": product.get("product_id") or product.get("ProductId"),
                "Ordination": idx,
                "Discount": discount * 100,
                "OtherProperties": [
                    {
                        "FieldKey": "quote_product_76A1F57A-B40F-4C4E-B412-44361EB118D8",  # Cor
                        "IntegerValue": product.get("color_id") or product.get("IdCor"),
                    },
                    {
                        "FieldKey": "quote_product_E426CC8C-54CB-4B9C-8E4D-93634CF93455",  # valor unit. c/ desconto
                        "DecimalValue": unit_price,
                    },
                    {
                        "FieldKey": "quote_product_4D6B83EE-8481-46B2-A147-1836B287E14C",  # prazo dias
                        "StringValue": f"{prazo};",
                    },
                    {
                        "FieldKey": "quote_product_7FD5E293-CBB5-43C8-8ABF-B9611317DF75",  # % de desconto
                        "DecimalValue": discount * 100,
                    },
                ],
            }
        )

    json_data = {
        "DealId": deal_id,
        "OwnerId": owner_id,
        "TemplateId": 196596,
        "Amount": total,
        "Discount": 0,
        "InstallmentsAmountFieldKey": "quote_amount",
        "Notes": observacao,
        "Sections": [
            {
                "Code": 0,
                "Total": total,
                "OtherProperties": [
                    {
                        "FieldKey": "quote_section_8136D2B9-1496-4C52-AB70-09B23A519286",  # Prazo conjunto
                        "StringValue": "045;",
                    },
                    {
                        "FieldKey": "quote_section_0F38DF78-FE65-471C-A391-9E8759470D4E",  # Total
                        "DecimalValue": total,
                    },
                    {
                        "FieldKey": "quote_section_64320D57-6350-44AB-B849-6A6110354C79",  # Total de itens
                        "IntegerValue": total_itens,
                    },
                ],
                "Products": products,
            }
        ],
        "OtherProperties": [
            {
                "FieldKey": "quote_0FB9F0CB-2619-44C5-92BD-1A2D2D818BFE",  # Forma de pagamento (Id)
                "IntegerValue": forma_pagamento_id_tipo2,
            },
            {
                "FieldKey": "quote_DE50A0F4-1FBE-46AA-9B5D-E182533E4B4A",  # Texto simples
                "StringValue": forma_pagamento_name,
            },
            {
                "FieldKey": "quote_E85539A9-D0D3-488E-86C5-66A49EAF5F3A",  # Condições de pagamento
                "IntegerValue": forma_pagamento,
            },
            {
                "FieldKey": "quote_F879E39D-E6B9-4026-8B4E-5AD2540463A3",  # Tipo de frete
                "IntegerValue": tipo_frete,
            },
            {
                "FieldKey": "quote_6D0FC2AB-6CCC-4A65-93DD-44BF06A45ABE",  # Validade
                "IntegerValue": 18826538,
            },
            {
                "FieldKey": "quote_520B942C-F3FD-4C6F-B183-C2E8C3EB6A33",  # Dias para entrega
                "IntegerValue": max_prazo or 45,
            },
        ],
    }

    try:
        resp = requests.post("https://public-api2.ploomes.com/Quotes", headers=_ploomes_headers(), json=json_data, timeout=20)
    except Exception as exc:  # pragma: no cover - integração externa
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if resp.status_code not in (200, 201):
        return JsonResponse({"detail": "Erro ao criar proposta", "response": resp.text}, status=resp.status_code)

    quote_id = None
    resp_json = resp.json() if resp.content else {}
    if isinstance(resp_json, dict):
        values = resp_json.get("value") or []
        if values and isinstance(values, list):
            quote_id = values[0].get("Id")

    return JsonResponse({"detail": "Proposta criada com sucesso.", "quote_id": quote_id}, status=201)


@csrf_exempt
@require_POST
def ploomes_create_deal(request):
    """Cria uma deal/ordem no Ploomes e retorna o ID criado."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    title = payload.get("nomeCliente") # nome do cliente
    contact_id = payload.get("ContactId")
    person_id = payload.get("PersonId")
    owner_id = payload.get("OwnerId") or request.session.get("owner_id")

    if not title or not contact_id:
        return JsonResponse({"detail": "Informe nome do cliente e ContactId."}, status=400)

    deal_body = {
        "Title": title,
        "ContactId": contact_id,
        "OwnerId": owner_id,
        "StageId": 166905,  # Proposta
    }
    if person_id not in (None, "", "Null"):
        deal_body["PersonId"] = person_id

    try:
        create_resp = requests.post("https://public-api2.ploomes.com/Deals", headers=_ploomes_headers(), json=deal_body, timeout=15)
    except Exception as exc:  # pragma: no cover - integração externa
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if create_resp.status_code not in (200, 201):
        return JsonResponse({"detail": "Erro ao criar a ordem", "response": create_resp.text}, status=create_resp.status_code)

    created_json = create_resp.json()
    deal_id = None
    if isinstance(created_json, dict):
        values = created_json.get("value") or []
        if values and isinstance(values, list):
            deal_id = values[0].get("Id")

    if not deal_id:
        # fallback para buscar a Ç£ltima deal do contato
        params = {"$top": 1, "$filter": f"ContactId eq {contact_id}", "$orderby": "CreateDate desc"}
        lookup_resp = requests.get("https://public-api2.ploomes.com/Deals", headers=_ploomes_headers(), params=params, timeout=10)
        if lookup_resp.ok:
            results = lookup_resp.json().get("value") or []
            if results:
                deal_id = results[0].get("Id")

    if not deal_id:
        return JsonResponse({"detail": "Ordem criada, mas não foi possível obter o Id."}, status=201)

    return JsonResponse({"detail": "Ordem criada com sucesso.", "deal_id": deal_id}, status=201)


@csrf_exempt
@require_POST
def ploomes_update_deal_contact(request):
    """Atualiza o PersonId de um deal no Ploomes."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    deal_id = payload.get("deal_id") or payload.get("DealId")
    contact_id = payload.get("contact_id") or payload.get("PersonId")

    if not deal_id or not contact_id:
        return JsonResponse({"detail": "Informe deal_id e contact_id (PersonId)."}, status=400)

    try:
        resp = requests.patch(
            f"https://api2.ploomes.com/Deals({deal_id})",
            headers=_ploomes_headers(),
            json={"PersonId": contact_id},
            timeout=15,
        )
    except Exception as exc:  # pragma: no cover
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if resp.status_code not in (200, 204):
        return JsonResponse({"detail": "Erro ao atualizar contato do deal", "response": resp.text}, status=resp.status_code)

    return JsonResponse({"detail": "Contato atualizado no deal.", "deal_id": deal_id, "contact_id": contact_id})


@csrf_exempt
@require_POST
def ploomes_win_deal(request):
    """Marca um deal no Ploomes como ganho: altera o stage e chama o endpoint /Win."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    deal_id = payload.get("deal_id") or payload.get("DealId")

    if not deal_id:
        return JsonResponse({"detail": "Informe deal_id."}, status=400)

    headers = _ploomes_headers()

    # Step 1: Alterar o StageId para 230240
    try:
        resp_stage = requests.patch(
            f"https://public-api2.ploomes.com/Deals({deal_id})",
            headers=headers,
            json={"StageId": 230240},
            timeout=15,
        )
    except Exception as exc:  # pragma: no cover
        return JsonResponse({"detail": f"Erro ao alterar stage: {exc}"}, status=502)

    if resp_stage.status_code not in (200, 204):
        return JsonResponse(
            {"detail": "Erro ao alterar stage do deal", "response": resp_stage.text},
            status=resp_stage.status_code
        )

    # Step 2: Chamar o endpoint /Win para ganhar o deal (POST conforme API Ploomes)
    try:
        resp_win = requests.post(
            f"https://public-api2.ploomes.com/Deals({deal_id})/Win",
            headers=headers,
            timeout=15,
        )
    except Exception as exc:  # pragma: no cover
        return JsonResponse({"detail": f"Erro ao ganhar deal: {exc}"}, status=502)

    if resp_win.status_code not in (200, 204):
        return JsonResponse(
            {"detail": "Erro ao marcar deal como ganho", "response": resp_win.text},
            status=resp_win.status_code
        )
    
    return JsonResponse({"detail": "Deal marcado como ganho com sucesso.", "deal_id": deal_id})


@csrf_exempt
@require_POST
def ploomes_lose_deal(request):
    """Marca um deal no Ploomes como perdido (Lose) informando o motivo."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    deal_id = payload.get("deal_id") or payload.get("DealId")
    loss_reason_id = payload.get("loss_reason_id") or payload.get("LossReasonId")

    if not deal_id or loss_reason_id in (None, ""):
        return JsonResponse({"detail": "Informe deal_id e loss_reason_id."}, status=400)

    headers = _ploomes_headers()

    try:
        resp_lose = requests.post(
            f"https://public-api2.ploomes.com/Deals({deal_id})/Lose",
            headers=headers,
            json={"LossReasonId": int(loss_reason_id)},
            timeout=15,
        )
    except Exception as exc:  # pragma: no cover
        return JsonResponse({"detail": f"Erro ao perder deal: {exc}"}, status=502)

    if resp_lose.status_code not in (200, 204):
        return JsonResponse(
            {"detail": "Erro ao marcar deal como perdido", "response": resp_lose.text},
            status=resp_lose.status_code,
        )

    return JsonResponse({"detail": "Deal marcado como perdido com sucesso.", "deal_id": deal_id, "loss_reason_id": int(loss_reason_id)})


@csrf_exempt
@require_POST
def ploomes_create_sale(request):
    """Cria uma venda (Order) no Ploomes após ganhar a proposta."""
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    deal_id = payload.get("deal_id") or payload.get("DealId")
    quote_id = payload.get("quote_id") or payload.get("QuoteId")

    if not deal_id or not quote_id:
        return JsonResponse({"detail": "Informe deal_id e quote_id."}, status=400)

    result = _criar_venda_from_quote(deal_id, quote_id)
    
    if not result.get("success"):
        return JsonResponse(result, status=400)
    
    return JsonResponse(result, status=201)


@csrf_exempt
def ploomes_quote_review(request, quote_id: int):
    """Envia uma revisão de proposta (Quote) para o Ploomes.

    Este endpoint existe para evitar expor o User-Key no frontend e contornar CORS.
    Ele aceita o mesmo payload simplificado usado no fluxo de criação (DealId/PaymentId/products)
    e monta o JSON final compatível com o Ploomes antes de chamar:
      POST https://api2.ploomes.com/Quotes(<id>)/Review
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    # Se o frontend mandar o JSON pronto no formato do Ploomes (Id/Sections/OtherProperties),
    # apenas validamos e encaminhamos.
    if isinstance(payload, dict) and ("Sections" in payload or "OtherProperties" in payload or "Id" in payload):
        if payload.get("Id") not in (None, ""):
            try:
                if int(payload.get("Id")) != int(quote_id):
                    return JsonResponse({"detail": "Id do payload não confere com a URL."}, status=400)
            except Exception:
                return JsonResponse({"detail": "Id inválido no payload."}, status=400)

        payload["Id"] = int(quote_id)

        try:
            resp = requests.post(
                f"https://api2.ploomes.com/Quotes({quote_id})/Review",
                headers=_ploomes_headers(),
                json=payload,
                timeout=20,
            )
        except Exception as exc:  # pragma: no cover - integração externa
            return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

        if resp.status_code not in (200, 201, 204):
            return JsonResponse({"detail": "Erro ao revisar proposta", "response": resp.text}, status=resp.status_code)

        if resp.content:
            try:
                return JsonResponse(resp.json(), status=resp.status_code, safe=False)
            except Exception:
                return JsonResponse({"detail": "Revisão enviada.", "response": resp.text}, status=resp.status_code)

        return JsonResponse({"detail": "Revisão enviada."}, status=resp.status_code)

    # Caso contrário, aceitamos um payload simplificado e montamos o JSON final.
    deal_id = payload.get("DealId") or payload.get("deal_id")
    pessoa_id = payload.get("PersonId") or payload.get("person_id")
    forma_pagamento = payload.get("PaymentId")
    forma_pagamento_name = payload.get("paymentName")
    forma_pagamento_id_tipo2 = payload.get("PaymentIdTipo2")
    observacao = payload.get("observacao") or payload.get("notes") or ""
    owner_id = payload.get("OwnerId") or payload.get("owner_id") or request.session.get("owner_id")
    uf = (payload.get("uf") or "").strip().upper()

    print(payload)

    if uf:
        if uf == "CE":
            tipo_frete = 57972827
        else:
            tipo_frete = 22886508
    else:
        tipo_frete = 22886508

    products_payload = payload.get("products") or _zip_products_from_arrays(payload)

    if not deal_id or not products_payload:
        return JsonResponse({"detail": "Informe DealId e pelo menos um produto."}, status=400)

    total = 0
    total_itens = 0
    max_prazo = 0
    products = []

    def _pad_prazo(value: int) -> str:
        try:
            return f"{int(value):03d};"
        except Exception:
            return "045;"

    for idx, product in enumerate(products_payload):
        qty = max(1, int(product.get("quantity", 1) or 1))
        line_total = float(product.get("total", 0) or 0)
        unit_price = float(product.get("unit_price", 0) or 0) or (line_total / qty if qty else 0)
        discount = float(product.get("discount_percent", 0) or 0)
        prazo = product.get("prazo") or 0
        try:
            group_id = product.get("group_id") or product.get("groupId") or product.get("GroupId")
            if group_id:
                gp = GrupoPrazo.objects.filter(grupo_code=str(group_id)).first()
                if gp and gp.prazo is not None:
                    prazo = gp.prazo
        except Exception:
            pass
        max_prazo = max(max_prazo, prazo or 0)

        total += line_total
        total_itens += qty

        # total sem desconto (base) = (unit_price / (1 - desconto)) * qty
        if discount and discount < 100:
            unit_sem_desconto = unit_price / (1 - (discount / 100))
        else:
            unit_sem_desconto = unit_price
        total_sem_desconto = unit_sem_desconto * qty

        products.append(
            {
                "Quantity": qty,
                "UnitPrice": unit_price,
                "Total": line_total,
                "ProductId": product.get("product_id") or product.get("ProductId"),
                "Ordination": idx,
                "Discount": discount * 100,
                "OtherProperties": [
                    {
                        "FieldKey": "quote_product_76A1F57A-B40F-4C4E-B412-44361EB118D8",  # Cor
                        "IntegerValue": product.get("color_id") or product.get("IdCor"),
                    },
                    {
                        "FieldKey": "quote_product_E426CC8C-54CB-4B9C-8E4D-93634CF93455",  # valor unit. c/ desconto
                        "DecimalValue": unit_price,
                    },
                    {
                        "FieldKey": "quote_product_4D6B83EE-8481-46B2-A147-1836B287E14C",  # prazo dias
                        "StringValue": _pad_prazo(prazo or 45),
                    },
                    {
                        "FieldKey": "quote_product_7FD5E293-CBB5-43C8-8ABF-B9611317DF75",  # % de desconto
                        "DecimalValue": (discount * 100) if discount else None,
                    },
                    {
                        "FieldKey": "quote_product_A0AED1F2-458F-47D3-BA29-C235BDFC5D55",  # Total sem desconto
                        "DecimalValue": total_sem_desconto,
                    },
                ],
            }
        )

    json_data = {
        "Id": int(quote_id),
        "DealId": deal_id,
        "PersonId": pessoa_id,
        "OwnerId": owner_id,
        "TemplateId": 196596,
        "Amount": total,
        "InstallmentsAmountFieldKey": "quote_amount",
        "Notes": observacao,
        "Sections": [
            {
                "Code": 0,
                "Total": total,
                "OtherProperties": [
                    {
                        "FieldKey": "quote_section_8136D2B9-1496-4C52-AB70-09B23A519286",  # Prazo conjunto
                        "StringValue": _pad_prazo(max_prazo or 45),
                    },
                    {
                        "FieldKey": "quote_section_0F38DF78-FE65-471C-A391-9E8759470D4E",  # Total
                        "DecimalValue": total,
                    },
                    {
                        "FieldKey": "quote_section_64320D57-6350-44AB-B849-6A6110354C79",  # Total de itens
                        "IntegerValue": total_itens,
                    },
                ],
                "Products": products,
            }
        ],
        "OtherProperties": [
            {
                "FieldKey": "quote_E85539A9-D0D3-488E-86C5-66A49EAF5F3A", # Id forma de pagamento
                "IntegerValue": int(forma_pagamento)
            },
            {
                "FieldKey": "quote_DE50A0F4-1FBE-46AA-9B5D-E182533E4B4A",  # Texto simples
                "StringValue": forma_pagamento_name,
            },
            {
                "FieldKey": "quote_520B942C-F3FD-4C6F-B183-C2E8C3EB6A33",  # Prazo de entrega
                "IntegerValue": max_prazo or 45,
            },
            {
                "FieldKey": "quote_82F9DE57-6E06-402A-A444-47F350284117",  # Atualizar dados
                "BoolValue": 'true',
            },
            {
                "FieldKey": "quote_6D0FC2AB-6CCC-4A65-93DD-44BF06A45ABE", # validade da proposta
                "IntegerValue" : 18826538
            },
            {
                "FieldKey": "quote_16CDE30A-C6F1-4998-8B73-661CF89160B8", # flag permitido
                "StringValue" : "Permitido"
            },
            {
                "FieldKey": "quote_F879E39D-E6B9-4026-8B4E-5AD2540463A3",  # Tipo de frete
                "IntegerValue": tipo_frete,
            },

        ],
    }
    
    print(json_data)

    try:
        resp = requests.post(
            f"https://api2.ploomes.com/Quotes({quote_id})/Review",
            headers=_ploomes_headers(),
            json=json_data,
            timeout=20,
        )
    except Exception as exc:  # pragma: no cover - integração externa
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    if resp.status_code not in (200, 201, 204):
        return JsonResponse({"detail": "Erro ao revisar proposta", "response": resp.text}, status=resp.status_code)

    if resp.content:
        try:
            return JsonResponse(resp.json(), status=resp.status_code, safe=False)
        except Exception:
            return JsonResponse({"detail": "Revisão enviada.", "response": resp.text}, status=resp.status_code)

    return JsonResponse({"detail": "Revisão enviada."}, status=resp.status_code)


@require_GET
def family_photo(request):
    family = request.GET.get("family") or request.GET.get("code") or request.GET.get("product_code") or ""
    if not family:
        return JsonResponse({"detail": "Parametro 'family' e obrigatorio."}, status=400)

    photo = FamilyPhoto.objects.filter(family=family).order_by("-uploaded_at").first()
    if not photo or not photo.image:
        return JsonResponse({"family": family, "image_url": None})

    image_url = request.build_absolute_uri(photo.image.url)
    return JsonResponse({"family": family, "product": photo.product, "image_url": image_url})

# compat alias
product_photo = family_photo


@csrf_exempt
@require_GET
def list_favorites(request):
    price_list = request.GET.get("priceList")

    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    items = FavoriteItem.objects.filter(owner_id=request.session.get("owner_id"), list_code=price_list).order_by("-created_at")
    data = [
        {
            "product_code": item.product_code,
        }
        for item in items
    ]
    return JsonResponse({"items": data})


@csrf_exempt
@require_POST
def add_favorite(request):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    fav, created = FavoriteItem.objects.get_or_create(
        owner_id=request.session.get("owner_id"),
        product_code=data.get("product_code", ""),
        list_code=data.get("price_list", ""),
    )
    if not created:
        fav.save()
    return JsonResponse({"detail": "Favorito salvo.", "id": fav.id})


@csrf_exempt
@require_POST
def delete_favorite(request):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        return JsonResponse({"detail": "Payload inválido."}, status=400)

    product_code = data.get("product_code", "")
    list_code = data.get("price_list", "")
    FavoriteItem.objects.filter(
        owner_id=request.session.get("owner_id"), product_code=product_code, list_code=list_code
    ).delete()
    return JsonResponse({"detail": "Favorito removido."})

@require_GET
def list_cart(request):
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    items = CartItem.objects.filter(owner_id=request.session.get("owner_id")).order_by("-created_at")
    data = [
        {
            "id": item.id,
            "product_code": item.product_code,
            "description": item.description,
            "list_name": item.list_name,
            "color": item.color,
            "price": float(item.price),
            "discount_percent": float(item.discount_percent),
            "final_price": float(item.final_price),
            "favorite": item.favorite,
            "quantity": item.quantity,
            "created_at": item.created_at.isoformat(),
        }
        for item in items
    ]
    return JsonResponse({"items": data})

@require_GET
def json_produtos_innovaro(request):
    """
    Retorna os dados da tabela ProdutoInnovaro em JSON
    Estrutura compatível com o frontend atual
    """
    produtos = (
        ProdutoInnovaro.objects
        .all()
        .values(
            "codigo",
            "chave",
            "nome",
            'modelo',
            'modelo_simples',
            'classe',
            'desc_generica',
            'tamanho',
            'capacidade',
            'rodado',
            'mola',
            'freio',
            'eixo',
            'pneu',
            'cor',
            'funcionalidade',
            'observacao',
            'crm',
        )
    )

    return JsonResponse(
        {
            "produtos": list(produtos)
        },
        safe=False
    )

@require_GET
def json_precos_produto(request):
    """
    PrecoProduto
    - Usa .values() (menos memória)
    - Agrupamento otimizado com defaultdict
    """
    rows = (
        PrecoProduto.objects
        .values(
            "tabela_codigo",
            "tabela_nome",
            "produto",
            "valor",
        )
        .order_by("tabela_codigo")
    )

    tabelas = defaultdict(lambda: {"codigo": "", "nome": "", "precos": []})

    for r in rows:
        tabela = tabelas[r["tabela_codigo"]]

        if not tabela["codigo"]:
            tabela["codigo"] = r["tabela_codigo"]
            tabela["nome"] = r["tabela_nome"]

        tabela["precos"].append({
            "produto": r["produto"],
            "descricao": r["produto"],
            "valor": str(r["valor"]),
        })

    return JsonResponse({"tabelaPreco": list(tabelas.values())})

@require_GET
def ploomes_users(request):
    """
    Consulta usuários no Ploomes.
    
    Retorna: id, name, profileid, suspended
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    
    url = "https://api2.ploomes.com/Users"
    
    try:
        resp = requests.get(url, headers=_ploomes_headers(), timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)
    
    data = resp.json()
    
    # Extrair apenas as colunas solicitadas
    users = []
    if isinstance(data, dict) and "value" in data:
        # Se a resposta é um OData com "value"
        users_list = data.get("value", [])
    elif isinstance(data, list):
        # Se a resposta é uma lista direto
        users_list = data
    else:
        users_list = []
    
    for user in users_list:
        users.append({
            "id": user.get("id"),
            "name": user.get("name"),
            "profileid": user.get("profileid"),
            "suspended": user.get("suspended"),
        })
    
    return JsonResponse({
        "count": len(users),
        "results": users,
    })


def ploomes_manage_users(request):
    """
    Página para gerenciar acesso dos usuários do Ploomes no sistema.
    Mostra quem já tem acesso (PortalUser) e permite criar novos acessos.
    """
    if not request.session.get("owner_id"):
        return redirect("login")
    
    # Buscar usuários da API Ploomes
    url = "https://api2.ploomes.com/Users"
    
    try:
        resp = requests.get(url, headers=_ploomes_headers(), timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        messages.error(request, f"Erro ao consultar usuários Ploomes: {exc}")
        return render(request, "sales/manage_users.html", {"users": [], "error": str(exc)})
    
    data = resp.json()
    
    # Extrair usuários da resposta
    if isinstance(data, dict) and "value" in data:
        users_list = data.get("value", [])
    elif isinstance(data, list):
        users_list = data
    else:
        users_list = []
    
    # Buscar usuários com acesso já criado
    portal_users = {pu.owner_id: pu for pu in PortalUser.objects.all()}
    
    # Preparar dados com status de acesso
    users_with_access = []
    for user in users_list:
        # Tenta diferentes formas de acessar os campos (case-insensitive)
        user_id = user.get("id") or user.get("Id") or user.get("ID")
        name = user.get("name") or user.get("Name") or user.get("NAME")
        profileid = user.get("profileid") or user.get("ProfileId") or user.get("profileId")
        suspended = user.get("suspended") or user.get("Suspended")
        
        has_access = user_id in portal_users if user_id else False
        portal_user = portal_users.get(user_id) if has_access else None
        price_lists_display = ""
        if portal_user:
            price_lists_display = ", ".join(portal_user.price_lists.values_list("name", flat=True))
        
        users_with_access.append({
            "id": user_id,
            "name": name,
            "profileid": profileid,
            "suspended": suspended,
            "has_access": has_access,
            "portal_user": portal_user,
            "price_lists_display": price_lists_display,
            "raw_user": user,  # Debug: adicionar dados brutos
        })
    
    return render(request, "sales/manage_users.html", {
        "users": users_with_access,
        "total_users": len(users_with_access),
        "user_name": request.session.get("user_name", "Usuário"),
    })


@require_GET
def ploomes_users_debug(request):
    """
    Endpoint de debug para ver a estrutura exata dos dados da API.
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    
    url = "https://api2.ploomes.com/Users"
    
    try:
        resp = requests.get(url, headers=_ploomes_headers(), timeout=15)
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)
    
    data = resp.json()
    return JsonResponse(data, safe=False)


@require_GET
def ploomes_contact_price_list(request):
    """
    Busca a lista de preco do cliente (Contact) no Ploomes.
    Querystring: contact_id
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    contact_id = request.GET.get("contact_id")
    try:
        contact_id = int(contact_id)
    except (TypeError, ValueError):
        return JsonResponse({"detail": "contact_id invalido."}, status=400)

    params = {
        "$select": "Id,Name",
        "$filter": f"Id eq {contact_id} and OtherProperties/any(op:op/FieldKey eq 'contact_70883643-FFE7-4C84-8163-89242423A4EF')",
        "$expand": "OtherProperties($filter=FieldKey eq 'contact_70883643-FFE7-4C84-8163-89242423A4EF';$select=ObjectValueName)",
    }

    try:
        resp = requests.get(
            "https://public-api2.ploomes.com/Contacts",
            headers=_ploomes_headers(),
            params=params,
            timeout=15,
        )
        resp.raise_for_status()
    except requests.exceptions.RequestException as exc:
        return JsonResponse({"detail": f"Erro na chamada Ploomes: {exc}"}, status=502)

    data = resp.json()
    values = data.get("value") if isinstance(data, dict) else None
    if not values:
        return JsonResponse({"price_list": None})

    other_props = values[0].get("OtherProperties") or []
    price_list = None
    if other_props:
        price_list = other_props[0].get("ObjectValueName")

    return JsonResponse({"price_list": price_list})

@csrf_exempt
@require_POST
def ploomes_create_user_access(request):
    """
    Cria um novo PortalUser vinculando com um usuário do Ploomes.
    
    Params (POST):
    - ploomes_user_id: ID do usuário no Ploomes
    - login: Login desejado (opcional, padrão: nome do usuário)
    - name: Nome do usuário (vem do Ploomes)
    - password: Senha do usuário
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Não autenticado."}, status=401)
    
    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON inválido."}, status=400)
    
    ploomes_user_id = data.get("ploomes_user_id")
    login = data.get("login")
    name = data.get("name")
    password = data.get("password")
    price_lists = data.get("price_lists") or []
    
    if not ploomes_user_id or not name or not password:
        return JsonResponse({"detail": "ploomes_user_id, name e password são obrigatórios."}, status=400)
    
    if len(password) < 6:
        return JsonResponse({"detail": "A senha deve ter pelo menos 6 caracteres."}, status=400)

    if not isinstance(price_lists, list):
        return JsonResponse({"detail": "price_lists deve ser uma lista."}, status=400)

    invalid_lists = [name for name in price_lists if name not in PRICE_LIST_OPTIONS]
    if invalid_lists:
        return JsonResponse({"detail": "Lista(s) de preco invalida(s)."}, status=400)
    
    # Verificar se já existe acesso
    if PortalUser.objects.filter(owner_id=ploomes_user_id).exists():
        return JsonResponse({"detail": "Este usuário já possui acesso no sistema."}, status=400)
    
    # Gerar login se não fornecido
    if not login:
        login = name.lower().replace(" ", "_")[:20]
    
    # Garantir login único
    base_login = login
    counter = 1
    while PortalUser.objects.filter(login=login).exists():
        login = f"{base_login}_{counter}"
        counter += 1
    
    try:
        # Criar novo PortalUser com a senha fornecida
        portal_user = PortalUser.objects.create(
            owner_id=ploomes_user_id,
            login=login,
            name=name,
            price_list=price_lists[0] if price_lists else None,
            password=password,
        )

        if price_lists:
            selected_lists = []
            for name in price_lists:
                price_list_obj, _ = PriceList.objects.get_or_create(name=name)
                selected_lists.append(price_list_obj)
            portal_user.price_lists.set(selected_lists)
        
        return JsonResponse({
            "detail": "Acesso criado com sucesso.",
            "portal_user": {
                "id": portal_user.id,
                "owner_id": portal_user.owner_id,
                "login": portal_user.login,
                "name": portal_user.name,
                "price_lists": list(portal_user.price_lists.values_list("name", flat=True)),
            }
        }, status=201)
    
    except Exception as exc:
        return JsonResponse({"detail": f"Erro ao criar acesso: {exc}"}, status=500)


@csrf_exempt
@require_POST
def ploomes_update_user_access(request):
    """
    Atualiza dados do PortalUser.
    Params (POST):
    - ploomes_user_id: ID do usuario no Ploomes
    - login: Login desejado (opcional)
    - password: Senha do usuario (opcional)
    - price_lists: Lista de listas de preco (opcional)
    """
    if not request.session.get("owner_id"):
        return JsonResponse({"detail": "Nao autenticado."}, status=401)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({"detail": "JSON invalido."}, status=400)

    ploomes_user_id = data.get("ploomes_user_id")
    login = data.get("login")
    password = data.get("password")
    price_lists = data.get("price_lists")

    if not ploomes_user_id:
        return JsonResponse({"detail": "ploomes_user_id e obrigatorio."}, status=400)

    try:
        portal_user = PortalUser.objects.get(owner_id=ploomes_user_id)
    except PortalUser.DoesNotExist:
        return JsonResponse({"detail": "Acesso nao encontrado."}, status=404)

    if login is not None:
        login = (login or "").strip()
        if not login:
            return JsonResponse({"detail": "Login nao pode ser vazio."}, status=400)
        if PortalUser.objects.filter(login=login).exclude(id=portal_user.id).exists():
            return JsonResponse({"detail": "Login ja esta em uso."}, status=400)
        portal_user.login = login

    if password:
        if len(password) < 6:
            return JsonResponse({"detail": "A senha deve ter pelo menos 6 caracteres."}, status=400)
        portal_user.password = password

    if price_lists is not None:
        if not isinstance(price_lists, list):
            return JsonResponse({"detail": "price_lists deve ser uma lista."}, status=400)
        invalid_lists = [name for name in price_lists if name not in PRICE_LIST_OPTIONS]
        if invalid_lists:
            return JsonResponse({"detail": "Lista(s) de preco invalida(s)."}, status=400)

        selected_lists = []
        for name in price_lists:
            price_list_obj, _ = PriceList.objects.get_or_create(name=name)
            selected_lists.append(price_list_obj)
        portal_user.price_lists.set(selected_lists)
        portal_user.price_list = price_lists[0] if price_lists else None

    portal_user.save()

    return JsonResponse({
        "detail": "Acesso atualizado com sucesso.",
        "portal_user": {
            "id": portal_user.id,
            "owner_id": portal_user.owner_id,
            "login": portal_user.login,
            "name": portal_user.name,
            "price_lists": list(portal_user.price_lists.values_list("name", flat=True)),
        }
    })

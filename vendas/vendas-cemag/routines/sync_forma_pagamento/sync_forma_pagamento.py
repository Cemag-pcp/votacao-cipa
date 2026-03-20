#!/usr/bin/env python
"""Rotina de sincronização de formas de pagamento do Ploomes.

Busca todas as opções das tabelas de forma de pagamento no Ploomes (OptionsTables)
(TableId 31965 e 32062) e sincroniza na tabela local `sales.FormaPagamento`.

Padrão de execução (igual às outras rotinas em routines/):
- Pode ser usada no Django shell
- Pode ser executada diretamente via `python routines/sync_forma_pagamento/sync_forma_pagamento.py`
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from datetime import datetime

import django
import requests
from django.conf import settings


def _setup_django() -> None:
    """Configura o Django quando rodar como script."""
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cemag_vendas.settings")
    django.setup()


def _ploomes_headers() -> dict:
    token = getattr(settings, "CEMAG_API_TOKEN", "")
    return {"User-Key": token, "Content-Type": "application/json"}


@dataclass
class SyncFormaPagamentoStats:
    criadas: int = 0
    atualizadas: int = 0
    total_api: int = 0


def _fetch_ploomes_formas_pagamento(table_ids: tuple[int, ...] = (31965, 32062), page_size: int = 500) -> list[dict]:
    """Busca as opções de forma de pagamento do Ploomes com paginação ($top/$skip)."""
    url = "https://public-api2.ploomes.com/Fields@OptionsTables@Options"
    all_items: list[dict] = []
    skip = 0

    table_filter = " or ".join([f"TableId eq {int(t)}" for t in table_ids])

    while True:
        params = {
            "$select": "Id,Name,TableId",
            "$filter": f"({table_filter})",
            "$top": int(page_size),
            "$skip": int(skip),
        }

        resp = requests.get(url, params=params, headers=_ploomes_headers(), timeout=20)
        if not resp.ok:
            detail = ""
            try:
                detail = resp.text or ""
            except Exception:
                detail = ""
            raise RuntimeError(f"Erro ao consultar Ploomes (HTTP {resp.status_code}). {detail}".strip())

        payload = resp.json() if resp.content else {}
        values = payload.get("value") or []
        if not values:
            break

        all_items.extend(values)
        if len(values) < int(page_size):
            break

        skip += int(page_size)

    return all_items


def sincronizar_formas_pagamento(
    table_ids: tuple[int, ...] = (31965, 32062),
    page_size: int = 500,
    verbose: bool = True,
) -> SyncFormaPagamentoStats:
    """Sincroniza formas de pagamento do Ploomes com a base local.

    Args:
        table_ids: TableIds do Ploomes para formas de pagamento.
        page_size: Tamanho da página para paginação ($top).
        verbose: Exibe logs no console.

    Returns:
        SyncFormaPagamentoStats
    """
    from sales.models import FormaPagamento

    stats = SyncFormaPagamentoStats()

    if verbose:
        print("=" * 60)
        print("🔄 INICIANDO SINCRONIZAÇÃO DE FORMAS DE PAGAMENTO (PLOOMES)")
        print("=" * 60)
        print(f"⏰ Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("🌐 Fonte: https://public-api2.ploomes.com/Fields@OptionsTables@Options")
        print(f"🧾 TableIds: {', '.join(str(t) for t in table_ids)}")
        print()

    if not getattr(settings, "CEMAG_API_TOKEN", ""):
        raise RuntimeError("CEMAG_API_TOKEN não configurado no settings.py/.env")

    items = _fetch_ploomes_formas_pagamento(table_ids=table_ids, page_size=page_size)

    # Dedup defensivo (caso a paginação/ordenação do endpoint repita itens)
    seen = set()
    uniq_items = []
    for it in items:
        key = (it.get("TableId"), it.get("Id"))
        if key in seen:
            continue
        seen.add(key)
        uniq_items.append(it)
    items = uniq_items
    stats.total_api = len(items)

    if verbose:
        print(f"✅ {stats.total_api} forma(s) de pagamento encontrada(s) no Ploomes")

    for idx, it in enumerate(items, 1):
        table_id = it.get("TableId")
        pagamento_id = it.get("Id")
        name = (it.get("Name") or "").strip()
        if table_id is None or pagamento_id is None or not name:
            continue

        _, created = FormaPagamento.objects.update_or_create(
            table_id=int(table_id),
            pagamento_id=int(pagamento_id),
            defaults={"descricao": name},
        )

        if created:
            stats.criadas += 1
        else:
            stats.atualizadas += 1

        if verbose and idx % 500 == 0:
            print(f"  Processadas: {idx}/{stats.total_api}")

    if verbose:
        print()
        print("=" * 60)
        print("✅ SINCRONIZAÇÃO CONCLUÍDA")
        print("=" * 60)
        print("💳 Formas de pagamento:")
        print(f"   ├─ Criadas: {stats.criadas}")
        print(f"   └─ Atualizadas: {stats.atualizadas}")
        print("=" * 60)

    return stats


if __name__ == "__main__":
    _setup_django()
    try:
        sincronizar_formas_pagamento(verbose=True)
        raise SystemExit(0)
    except Exception as exc:
        print("=" * 60)
        print("❌ ERRO DURANTE A SINCRONIZAÇÃO")
        print("=" * 60)
        print(f"Erro: {exc}")
        raise SystemExit(1)

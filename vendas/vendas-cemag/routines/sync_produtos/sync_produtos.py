"""
Script para sincronizar produtos da API Innovaro com o banco de dados local.

Uso:
    python manage.py shell < routines/sync_produtos.py
    
    Ou dentro do Django shell:
    >>> from routines.sync_produtos import sync_produtos_innovaro
    >>> sync_produtos_innovaro()
"""

import os
import sys
import django
import requests
from datetime import datetime

# Configurar Django
if __name__ == "__main__":
    # Adicionar o diretório raiz ao path
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cemag_vendas.settings")
    django.setup()

from sales.models import ProdutoInnovaro


def sync_produtos_innovaro(verbose=True):
    """
    Sincroniza produtos da API Innovaro com o banco de dados local.
    Preenche `modelo_simples` a partir de `modelo`; se `modelo` estiver vazio, usa `codigo`.
    """
    API_URL = "https://cemag.innovaro.com.br/api/publica/v1/tabelas/listarProdutos"

    stats = {
        "criados": 0,
        "atualizados": 0,
        "erros": 0,
        "total_api": 0,
    }

    def simplificar_modelo(valor: str) -> str:
        m = (valor or "").strip()
        up = m.upper()
        if up.startswith("CBHM"):
            return "CBHM"
        if up.startswith("CBH"):
            return "CBH"
        if up.startswith("FT"):
            return "FTC"
        if up.startswith("F"):
            return "F"
        return m

    try:
        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Iniciando sincronização de produtos...")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Consultando API: {API_URL}")

        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()

        data = response.json()
        produtos = data.get("produtos", [])
        stats["total_api"] = len(produtos)

        if verbose:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Total de produtos na API: {stats['total_api']}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Processando produtos...")

        for idx, produto in enumerate(produtos, 1):
            try:
                codigo = (produto.get("codigo") or "").strip()
                chave = produto.get("chave")

                if not codigo or not chave:
                    if verbose:
                        print(f"  ⚠️  Produto sem código ou chave: {produto}")
                    stats["erros"] += 1
                    continue

                mola_freio = (produto.get("molaFreio") or "").strip()
                mola = mola_freio[0] if len(mola_freio) >= 1 else ""
                freio = mola_freio[1] if len(mola_freio) >= 2 else ""

                modelo = (produto.get("modelo") or "").strip()
                base_modelo = modelo if modelo else codigo  # <- regra: fallback no código

                produto_data = {
                    "nome": produto.get("nome", ""),
                    "modelo": modelo,
                    "modelo_simples": simplificar_modelo(base_modelo),
                    "classe": produto.get("classe", ""),
                    "desc_generica": produto.get("descGenerica", ""),
                    "tamanho": produto.get("tamanho", ""),
                    "capacidade": produto.get("capacidade", ""),
                    "rodado": produto.get("rodado", ""),
                    "mola_freio": mola_freio,
                    "mola": mola,
                    "freio": freio,
                    "eixo": produto.get("eixo", ""),
                    "pneu": produto.get("pneu", ""),
                    "cor": produto.get("cor", ""),
                    "funcionalidade": produto.get("funcionalidade", ""),
                    "observacao": produto.get("observacao", ""),
                    "crm": produto.get("CRM", False),
                }

                _, created = ProdutoInnovaro.objects.update_or_create(
                    codigo=codigo,
                    defaults={"chave": chave, **produto_data}
                )

                if created:
                    stats["criados"] += 1
                else:
                    stats["atualizados"] += 1

                if verbose and idx % 100 == 0:
                    print(f"  Processados: {idx}/{stats['total_api']} produtos...")

            except Exception as e:
                stats["erros"] += 1
                if verbose:
                    print(f"  ❌ Erro ao processar produto {produto.get('codigo', 'UNKNOWN')}: {e}")

        if verbose:
            print(f"\n{'='*60}")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Sincronização concluída!")
            print(f"{'='*60}")
            print(f"  📊 Total na API: {stats['total_api']}")
            print(f"  ✅ Criados: {stats['criados']}")
            print(f"  🔄 Atualizados: {stats['atualizados']}")
            print(f"  ❌ Erros: {stats['erros']}")
            print(f"{'='*60}\n")

        return stats

    except requests.RequestException as e:
        if verbose:
            print(f"❌ Erro ao consultar API: {e}")
        stats["erros"] = -1
        return stats

    except Exception as e:
        if verbose:
            print(f"❌ Erro inesperado: {e}")
        stats["erros"] = -1
        return stats


if __name__ == "__main__":
    # Executar sincronização
    sync_produtos_innovaro(verbose=True)

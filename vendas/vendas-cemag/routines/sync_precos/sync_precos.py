#!/usr/bin/env python
"""
Script para sincronizar listas de preços da API Innovaro
Busca dados de: http://cemag.innovaro.com.br/api/publica/v1/tabelas/listarPrecos
"""

import os
import sys
import django
import requests
from decimal import Decimal
from datetime import datetime

# Configurar Django
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "cemag_vendas.settings")
django.setup()

from sales.models import PrecoProduto

# URL da API
API_URL = "http://cemag.innovaro.com.br/api/publica/v1/tabelas/listarPrecos"


def limpar_valor(valor_str):
    """
    Converte string de valor monetário para Decimal
    Exemplo: "74.184,00" -> Decimal("74184.00")
    """
    if not valor_str:
        return Decimal("0.00")
    
    # Remove pontos de milhar e substitui vírgula por ponto
    valor_limpo = valor_str.replace(".", "").replace(",", ".")
    
    try:
        return Decimal(valor_limpo)
    except:
        print(f"⚠️  Erro ao converter valor: {valor_str}")
        return Decimal("0.00")


def sincronizar_precos():
    """
    Função principal que busca e sincroniza as listas de preços
    """
    print("=" * 60)
    print("🔄 INICIANDO SINCRONIZAÇÃO DE LISTAS DE PREÇOS")
    print("=" * 60)
    print(f"⏰ Horário: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print(f"🌐 API: {API_URL}")
    print()
    
    try:
        # Buscar dados da API
        print("📡 Buscando dados da API...")
        response = requests.get(API_URL, timeout=30)
        response.raise_for_status()
        dados = response.json()
        
        tabelas_api = dados.get("tabelaPreco", [])
        print(f"✅ {len(tabelas_api)} tabela(s) de preço encontrada(s)")
        print()
        
        total_precos_criados = 0
        total_precos_atualizados = 0
        
        # Processar cada tabela de preço
        for tabela_data in tabelas_api:
            tabela_codigo = tabela_data.get("codigo", "")
            tabela_nome = tabela_data.get("nome", "")
            precos_lista = tabela_data.get("precos", [])
            
            if not tabela_codigo or not tabela_nome:
                print(f"⚠️  Tabela sem código ou nome, pulando...")
                continue
            
            print(f"📋 Processando: {tabela_nome} ({tabela_codigo})")
            print(f"   └─ {len(precos_lista)} preço(s) na lista")
            
            # Processar preços
            for preco_data in precos_lista:
                produto = preco_data.get("produto", "")
                valor_str = preco_data.get("valor", "0,00")
                
                if not produto:
                    continue
                
                valor = limpar_valor(valor_str)
                
                # Criar ou atualizar preço
                preco, criado = PrecoProduto.objects.update_or_create(
                    tabela_codigo=tabela_codigo,
                    produto=produto,
                    defaults={
                        "tabela_nome": tabela_nome,
                        "valor": valor
                    }
                )
                
                if criado:
                    total_precos_criados += 1
                else:
                    total_precos_atualizados += 1
            
            print(f"   ✅ Preços sincronizados")
            print()
        
        # Resumo final
        print("=" * 60)
        print("✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO")
        print("=" * 60)
        print(f"💰 Preços de Produtos:")
        print(f"   ├─ Criados: {total_precos_criados}")
        print(f"   └─ Atualizados: {total_precos_atualizados}")
        print("=" * 60)
        
        return True
        
    except requests.exceptions.RequestException as e:
        print("=" * 60)
        print("❌ ERRO AO BUSCAR DADOS DA API")
        print("=" * 60)
        print(f"Erro: {e}")
        return False
        
    except Exception as e:
        print("=" * 60)
        print("❌ ERRO DURANTE A SINCRONIZAÇÃO")
        print("=" * 60)
        print(f"Erro: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    sucesso = sincronizar_precos()
    sys.exit(0 if sucesso else 1)

# Sincronização de Produtos Innovaro

Script para sincronizar produtos da API Innovaro com o banco de dados local.

## 📋 Descrição

Este script consulta a API pública da Innovaro e sincroniza todos os produtos no banco de dados local, criando novos registros ou atualizando os existentes.

## 🚀 Como Usar

### Opção 1: Executar diretamente
```bash
python routines/sync_produtos/sync_produtos.py
```

### Opção 2: Dentro do Django shell
```bash
python manage.py shell
```

Depois, no shell:
```python
from routines.sync_produtos.sync_produtos import sync_produtos_innovaro
stats = sync_produtos_innovaro(verbose=True)
print(f"Produtos criados: {stats['criados']}")
print(f"Produtos atualizados: {stats['atualizados']}")
```

### Opção 3: Importar em uma view ou comando
```python
from routines.sync_produtos.sync_produtos import sync_produtos_innovaro

# Executar sincronização
stats = sync_produtos_innovaro(verbose=True)
```

## 🔄 O que o script faz

1. Consulta a API: `https://cemag.innovaro.com.br/api/publica/v1/tabelas/listarProdutos`
2. Para cada produto retornado:
   - Verifica se já existe no banco (por código)
   - Se não existe, cria um novo registro
   - Se existe, atualiza os dados
3. Exibe estatísticas ao final:
   - Total de produtos na API
   - Produtos criados
   - Produtos atualizados
   - Erros encontrados

## 📊 Campos Sincronizados

O script sincroniza os seguintes campos do model `ProdutoInnovaro`:

| Campo | Descrição |
|-------|-----------|
| `codigo` | Código único do produto (SKU) |
| `chave` | Chave numérica única |
| `nome` | Nome completo do produto |
| `modelo` | Modelo do produto |
| `classe` | Classe/categoria |
| `desc_generica` | Descrição genérica |
| `tamanho` | Tamanho |
| `capacidade` | Capacidade |
| `rodado` | Tipo de rodado |
| `mola_freio` | Configuração de mola/freio |
| `eixo` | Configuração de eixo |
| `pneu` | Tipo de pneu |
| `cor` | Cor |
| `funcionalidade` | Funcionalidades |
| `observacao` | Observações |
| `crm` | Flag indicando se o produto está no CRM |

## 💡 Exemplos de Uso

### Buscar produtos sincronizados

```python
from sales.models import ProdutoInnovaro

# Buscar todos os produtos
produtos = ProdutoInnovaro.objects.all()

# Buscar por modelo
produtos_cbhm = ProdutoInnovaro.objects.filter(modelo="CBHM5000")

# Buscar por classe
carretas = ProdutoInnovaro.objects.filter(classe="Carretas Basculantes")

# Buscar produtos no CRM
produtos_crm = ProdutoInnovaro.objects.filter(crm=True)

# Buscar por código específico
produto = ProdutoInnovaro.objects.get(codigo="CBHM5000 GR SS RD M17")
```

## ⚙️ Retorno da Função

A função `sync_produtos_innovaro()` retorna um dicionário com estatísticas:

```python
{
    "total_api": 150,      # Total de produtos na API
    "criados": 10,         # Produtos criados
    "atualizados": 140,    # Produtos atualizados
    "erros": 0             # Erros encontrados (-1 se erro fatal)
}
```

## 🔧 Configuração

O script configura automaticamente o Django quando executado diretamente. Certifique-se de que:

- O arquivo `.env` está configurado corretamente
- O banco de dados está acessível
- As migrações foram executadas: `python manage.py migrate`

## 📝 Logs

O script exibe logs detalhados durante a execução:

```
[13:20:15] Iniciando sincronização de produtos...
[13:20:15] Consultando API: https://cemag.innovaro.com.br/...
[13:20:16] Total de produtos na API: 150
[13:20:16] Processando produtos...
  Processados: 100/150 produtos...
  
============================================================
[13:20:20] Sincronização concluída!
============================================================
  📊 Total na API: 150
  ✅ Criados: 10
  🔄 Atualizados: 140
  ❌ Erros: 0
============================================================
```

## ⚠️ Tratamento de Erros

- Produtos sem código ou chave são ignorados
- Erros individuais não interrompem o processo
- Erros de conexão com a API são reportados
- Todos os erros são contabilizados nas estatísticas

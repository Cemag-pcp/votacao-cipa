# Sincronização de Listas de Preços

Script para sincronizar listas de preços da API Innovaro com o banco de dados local.

## 📋 Descrição

Este script consulta a API pública da Innovaro e sincroniza todas as listas de preços e seus respectivos valores de produtos no banco de dados local.

## 🚀 Como Usar

### Opção 1: Dentro do Django shell
```bash
python manage.py shell
```

Depois, no shell:
```python
from routines.sync_precos.sync_precos import sincronizar_precos
sucesso = sincronizar_precos()
```

## 🔄 O que o script faz

1. Consulta a API: `http://cemag.innovaro.com.br/api/publica/v1/tabelas/listarPrecos`
2. Para cada tabela de preço retornada:
   - Para cada produto na lista:
     - Converte o valor de formato brasileiro (ex: "74.184,00") para Decimal
     - Cria ou atualiza o preço do produto no banco de dados
3. Exibe estatísticas ao final:
   - Preços criados
   - Preços atualizados

## 📊 Estrutura de Dados

### Model: `PrecoProduto`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `tabela_codigo` | CharField | Código da tabela de preço |
| `tabela_nome` | CharField | Nome da tabela de preço |
| `produto` | CharField | Código do produto (SKU) |
| `valor` | DecimalField | Valor em R$ |
| `created_at` | DateTimeField | Data de criação |
| `updated_at` | DateTimeField | Data da última atualização |

### Índices e Constraints

- **Unique Together**: `(tabela_codigo, produto)` - Garante que não haja duplicatas
- **Índices**: Otimizados para buscas por tabela, produto e combinação de ambos

## 💡 Exemplos de Uso

### Buscar preços sincronizados

```python
from sales.models import PrecoProduto

# Buscar todos os preços de uma tabela específica
precos_mt = PrecoProduto.objects.filter(tabela_codigo="Lista Preço MT")

# Buscar preço de um produto específico em uma tabela
preco = PrecoProduto.objects.get(
    tabela_codigo="Lista Preço MT",
    produto="CBH12 SS RS/T R15,5 M22"
)
print(f"Preço: R$ {preco.valor}")

# Listar todas as tabelas de preço disponíveis
tabelas = PrecoProduto.objects.values('tabela_codigo', 'tabela_nome').distinct()
for tabela in tabelas:
    print(f"{tabela['tabela_codigo']} - {tabela['tabela_nome']}")

# Buscar todos os preços de um produto em diferentes tabelas
precos_produto = PrecoProduto.objects.filter(
    produto="CBH12 SS RS/T R15,5 M22"
)
for preco in precos_produto:
    print(f"{preco.tabela_nome}: R$ {preco.valor}")
```

### Comparar preços entre tabelas

```python
from sales.models import PrecoProduto
from django.db.models import Q

# Comparar preço de um produto em duas tabelas
produto_codigo = "CBH12 SS RS/T R15,5 M22"
precos = PrecoProduto.objects.filter(
    produto=produto_codigo,
    tabela_codigo__in=["Lista Preço MT", "Lista Preço SP"]
)

for preco in precos:
    print(f"{preco.tabela_nome}: R$ {preco.valor}")
```

## ⚙️ Conversão de Valores

O script converte automaticamente valores do formato brasileiro para Decimal:

```python
# Formato da API: "74.184,00"
# Convertido para: Decimal("74184.00")

# Formato da API: "89.454,00"
# Convertido para: Decimal("89454.00")
```

## 🔧 Configuração

O script configura automaticamente o Django quando executado diretamente. Certifique-se de que:

- O arquivo `.env` está configurado corretamente
- O banco de dados está acessível
- As migrações foram executadas: `python manage.py migrate`

## 📝 Logs

O script exibe logs detalhados durante a execução:

```
============================================================
🔄 INICIANDO SINCRONIZAÇÃO DE LISTAS DE PREÇOS
============================================================
⏰ Horário: 08/01/2026 13:20:15
🌐 API: http://cemag.innovaro.com.br/api/publica/v1/tabelas/listarPrecos

📡 Buscando dados da API...
✅ 3 tabela(s) de preço encontrada(s)

📋 Processando: Lista Preço MT (Lista Preço MT)
   └─ 150 preço(s) na lista
   ✅ Preços sincronizados

📋 Processando: Lista Preço SP (Lista Preço SP)
   └─ 150 preço(s) na lista
   ✅ Preços sincronizados

============================================================
✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO
============================================================
💰 Preços de Produtos:
   ├─ Criados: 250
   └─ Atualizados: 50
============================================================
```

## ⚠️ Tratamento de Erros

- Tabelas sem código ou nome são ignoradas
- Produtos sem código são ignorados
- Valores inválidos são convertidos para 0.00
- Erros de conexão com a API são reportados
- Erros não interrompem o processo de sincronização

## 🔄 Retorno da Função

A função `sincronizar_precos()` retorna:

- `True`: Se a sincronização foi bem-sucedida
- `False`: Se houve erro de conexão ou processamento

## 📌 Notas Importantes

1. **Atualização Incremental**: O script usa `update_or_create`, então:
   - Novos preços são criados
   - Preços existentes são atualizados com os valores mais recentes

2. **Performance**: O script processa todos os preços de uma vez. Para grandes volumes, considere adicionar paginação ou processamento em lotes.

3. **Unicidade**: A combinação `(tabela_codigo, produto)` é única, garantindo que não haja duplicatas.

4. **Timezone**: Os timestamps são salvos no timezone configurado no Django.

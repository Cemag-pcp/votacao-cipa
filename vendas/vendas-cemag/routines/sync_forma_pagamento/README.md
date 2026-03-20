# Sincronização de Formas de Pagamento (Ploomes)

Script para sincronizar as formas de pagamento do Ploomes com o banco de dados local do sistema.

## 📋 Descrição

Este script consulta a API pública do Ploomes (OptionsTables) para obter todas as opções de **formas de pagamento** e faz **upsert** (cria/atualiza) na tabela local `sales.FormaPagamento`.

Atualmente são sincronizadas as opções de duas tabelas do Ploomes:

- **TableId 32062**
- **TableId 31965**

(esses são os mesmos TableIds usados pelo endpoint existente `api/ploomes/payment-id/`.)

## 🚀 Como Usar

### Opção 1: Dentro do Django shell

```bash
python manage.py shell
```

Depois, no shell:

```python
from routines.sync_forma_pagamento.sync_forma_pagamento import sincronizar_formas_pagamento
stats = sincronizar_formas_pagamento()
print(stats)
```

### Opção 2: Executar diretamente como script

```bash
python routines/sync_forma_pagamento/sync_forma_pagamento.py
```

## 🔄 O que o script faz

1. Consulta a API do Ploomes:
   - Endpoint: `https://public-api2.ploomes.com/Fields@OptionsTables@Options`
   - Filtro: `(TableId eq 31965 or TableId eq 32062)`
   - Campos: `Id`, `Name`, `TableId`
   - Paginação: usa `$top` e `$skip` para buscar tudo

2. Para cada opção retornada:
   - Salva `TableId` (origem)
   - Salva `Id` como `pagamento_id`
   - Salva `Name` como `descricao`
   - Executa `update_or_create` no banco local

3. Exibe estatísticas ao final:
   - Registros criados
   - Registros atualizados

## 📊 Estrutura de Dados

### Model: `FormaPagamento`

| Campo | Tipo | Descrição |
|------|------|-----------|
| `table_id` | PositiveIntegerField | TableId do Ploomes (qual tabela originou a opção) |
| `pagamento_id` | PositiveIntegerField | ID da opção no Ploomes |
| `descricao` | CharField | Nome/descrição |
| `created_at` | DateTimeField | Data de criação |
| `updated_at` | DateTimeField | Data de atualização |

### Índices e Constraints

- **Unique Together**: `(table_id, pagamento_id)`
- **Index**: `(table_id, pagamento_id)`

## ⚙️ Configuração

O script usa o mesmo token do Ploomes já utilizado pelo sistema:

- `CEMAG_API_TOKEN` em `cemag_vendas.settings`

Se o token não estiver configurado, o script aborta com erro.

## 📝 Logs

Exemplo de saída:

```
============================================================
🔄 INICIANDO SINCRONIZAÇÃO DE FORMAS DE PAGAMENTO (PLOOMES)
============================================================
⏰ Horário: 15/01/2026 10:20:15
🌐 Fonte: https://public-api2.ploomes.com/Fields@OptionsTables@Options
🧾 TableIds: 31965, 32062

✅ 40 forma(s) de pagamento encontrada(s) no Ploomes

============================================================
✅ SINCRONIZAÇÃO CONCLUÍDA
============================================================
💳 Formas de pagamento:
   ├─ Criadas: 10
   └─ Atualizadas: 30
============================================================
```

## ⚠️ Notas Importantes

1. **Não remove opções**: o script apenas cria/atualiza. Se uma opção for removida do Ploomes, ela continuará no banco local.
2. **Paginação**: o script usa paginação para evitar limite de retorno.
3. **Dois TableIds**: o mesmo `Id` pode existir em tabelas diferentes; por isso a chave única é `(table_id, pagamento_id)`.

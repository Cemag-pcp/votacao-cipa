# Sincronização de Cores (Ploomes)

Script para sincronizar a tabela de cores do Ploomes com o banco de dados local do sistema.

## 📋 Descrição

Este script consulta a API pública do Ploomes (OptionsTables) para obter todas as cores cadastradas e faz **upsert** (cria/atualiza) na tabela local `sales.Cores`.

A tabela de cores no Ploomes usada aqui é a **OptionsTable TableId = 36909**.

## 🚀 Como Usar

### Opção 1: Dentro do Django shell

```bash
python manage.py shell
```

Depois, no shell:

```python
from routines.sync_cores.sync_cores import sincronizar_cores
stats = sincronizar_cores()
print(stats)
```

### Opção 2: Executar diretamente como script

```bash
python routines/sync_cores/sync_cores.py
```

## 🔄 O que o script faz

1. Consulta a API do Ploomes:
   - Endpoint: `https://public-api2.ploomes.com/Fields@OptionsTables@Options`
   - Filtro: `TableId eq 36909`
   - Campos: `Id`, `Name`, `TableId`
   - Paginação: usa `$top` e `$skip` para buscar tudo

2. Para cada cor retornada:
   - Usa `Id` como `cor_id`
   - Usa `Name` como `descricao`
   - Executa `update_or_create` no banco local

3. Exibe estatísticas ao final:
   - Cores criadas
   - Cores atualizadas

## 📊 Estrutura de Dados

### Model: `Cores`

| Campo | Tipo | Descrição |
|------|------|-----------|
| `cor_id` | PositiveIntegerField | ID da cor no Ploomes |
| `descricao` | CharField | Nome/descrição da cor |
| `created_at` | DateTimeField | Data de criação |
| `updated_at` | DateTimeField | Data de atualização |

### Índices e Constraints

- **Unique**: `cor_id` (evita duplicidades)
- **Index**: `cor_id` (buscas rápidas)

## ⚙️ Configuração

O script usa o mesmo token do Ploomes já utilizado pelo sistema:

- `CEMAG_API_TOKEN` em `cemag_vendas.settings`

Se o token não estiver configurado, o script aborta com erro.

## 📝 Logs

Exemplo de saída:

```
============================================================
🔄 INICIANDO SINCRONIZAÇÃO DE CORES (PLOOMES)
============================================================
⏰ Horário: 15/01/2026 10:20:15
🌐 Fonte: https://public-api2.ploomes.com/Fields@OptionsTables@Options (TableId=36909)

✅ 25 cor(es) encontrada(s) no Ploomes

============================================================
✅ SINCRONIZAÇÃO CONCLUÍDA
============================================================
🎨 Cores:
   ├─ Criadas: 10
   └─ Atualizadas: 15
============================================================
```

## ⚠️ Notas Importantes

1. **Não remove cores**: o script apenas cria/atualiza. Se uma cor for removida do Ploomes, ela continuará no banco local.
2. **Paginação**: o script usa paginação para evitar limite de retorno.
3. **Falha de autenticação**: se `CEMAG_API_TOKEN` estiver ausente ou inválido, a API retornará erro.

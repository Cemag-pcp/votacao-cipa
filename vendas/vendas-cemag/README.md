# Projeto Django - Vendas CEMAG

Aplicação Django para a equipe de vendedores da CEMAG, pronta para consultar uma API externa de vendedores e persistir os dados em banco.

## Requisitos
- Python 3.13+
- Virtualenv recomendado
- Dependências: `pip install -r requirements.txt`
- Banco: SQLite por padrão; Postgres/MySQL podem ser usados via variáveis de ambiente.

## Configuração rápida
1. Crie e ative um ambiente virtual (opcional):
   ```powershell
   python -m venv .venv
   .\.venv\Scripts\activate
   ```
2. Instale dependências:
   ```powershell
   pip install -r requirements.txt
   ```
3. Exporte variáveis (exemplos em Windows/Powershell):
   ```powershell
   $env:DJANGO_SECRET_KEY="sua-chave"
   $env:DJANGO_DEBUG="True"                # use False em produção
   $env:DJANGO_ALLOWED_HOSTS="sua.url.com,localhost"
   $env:DJANGO_CSRF_TRUSTED_ORIGINS="https://sua.url.com"

   # Banco
   $env:DB_ENGINE="django.db.backends.sqlite3"    # ou django.db.backends.postgresql
   $env:DB_NAME="db.sqlite3"                      # ou nome do banco
   $env:DB_USER=""
   $env:DB_PASSWORD=""
   $env:DB_HOST=""
   $env:DB_PORT=""

   # API externa
   $env:CEMAG_API_BASE_URL="https://api.exemplo.cemag.com.br"
   $env:CEMAG_API_TOKEN="token-api"
   ```
4. Rode migrações:
   ```powershell
   python manage.py migrate
   ```
5. Suba o servidor:
   ```powershell
   python manage.py runserver
   ```

## Endpoints principais
- `GET /api/vendors/`: retorna vendedores do banco.
  - Query `source=external` para buscar diretamente na API externa (sem salvar).
  - Query `limit=<n>` para limitar registros buscados externamente.
- `POST /api/vendors/sync/`: consulta a API externa e salva/atualiza vendedores no banco.
  - Body form opcional: `limit=<n>`.
  - CSRF está desativado neste endpoint pensando em integrações internas; habilite/proteja conforme necessidade de produção.

Exemplos com `curl` (via PowerShell):
```powershell
curl http://localhost:8000/api/vendors/
curl "http://localhost:8000/api/vendors/?source=external&limit=20"
curl -Method POST http://localhost:8000/api/vendors/sync/ -Body @{limit=50}
```

## Administração
- Crie um superusuário para acessar `/admin/`:
  ```powershell
  python manage.py createsuperuser
  ```

## Observações de integração
- O endpoint externo esperado é `${CEMAG_API_BASE_URL}/vendedores`, retornando lista ou objeto com chave `results`.
- Ajuste o mapeamento em `sales/services.py` caso o contrato da API seja diferente (nomes de campos, autenticação etc.).
- Para usar Postgres/MySQL, instale o driver correspondente (`psycopg2-binary`, `mysqlclient`) e ajuste `DB_ENGINE` e dados de conexão.
"# crm" 
# repvendas
# repvendas

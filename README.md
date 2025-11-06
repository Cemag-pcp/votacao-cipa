# Votação CIPA

## Requisitos

- Python 3.11+
- pip

"# votacao-cipa" 
## Instalação

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Execução

```bash
uvicorn main:app --reload
```

O servidor ficará disponível em `http://127.0.0.1:8000`. A documentação automática pode ser acessada em `http://127.0.0.1:8000/docs`.

### Navegação pela interface web

As páginas HTML utilizam Bootstrap e ficam disponíveis diretamente no servidor FastAPI:

- **Página inicial**: `http://127.0.0.1:8000/` — visão geral das sessões de votação cadastradas.
- **Lista de sessões**: `http://127.0.0.1:8000/sessions` — atalho para todas as sessões.
- **Detalhes da sessão**: `http://127.0.0.1:8000/sessions/<ID>` — substitua `<ID>` pelo identificador numérico da sessão.
- **Área do mesário**: `http://127.0.0.1:8000/sessions/<ID>/mesario`
- **Cabine de votação**: `http://127.0.0.1:8000/sessions/<ID>/cabine`

Os links acima pressupõem que existam registros no banco de dados SQLite local. Você pode usar os endpoints da API descritos na seção seguinte para criar sessões, candidatos e mesários antes de navegar pela interface.

## Fluxo Geral

1. **Criar a sessão** (`POST /api/sessions`). Informe o código (ex.: `2025.1`) e a quantidade esperada de votos.
2. **Cadastrar candidatos** (`POST /api/sessions/{session_id}/candidates`) com nome, matrícula e número da comissão.
3. **Cadastrar mesários** (`POST /api/sessions/{session_id}/poll_workers`).
4. **Iniciar a sessão** (`POST /api/sessions/{session_id}/start`). Depois disso, cadastros não devem ser alterados.
5. **Liberação de votos**:
   - O mesário chama `POST /api/sessions/{session_id}/permits` ou envia `{ "action": "authorize" }` pelo websocket `/ws/sessions/{session_id}/mesario`.
   - A cabine precisa estar conectada no websocket `/ws/sessions/{session_id}/cabine` para receber o token.
6. **Registrar o voto** (`POST /api/sessions/{session_id}/votes`) com o `candidate_id` escolhido e o `permit_token` recebido.
7. **Encerrar a sessão** (`POST /api/sessions/{session_id}/close`).
8. **Consultar resultados** (`GET /api/sessions/{session_id}/results`).

Cada voto recebe o horário de registro automaticamente e os tokens liberados são únicos e utilizados apenas uma vez.

## Comunicação em tempo real

- Websocket do mesário (`/ws/sessions/{session_id}/mesario`): envie `{ "action": "authorize" }` para gerar e receber um novo token e notificar as cabines conectadas.
- Websocket da cabine (`/ws/sessions/{session_id}/cabine`): recebe mensagens do tipo `{ "type": "vote_permit", "token": "..." }` com o token autorizado mais recente.

## Estrutura do Projeto

```
app/
├── api/
│   └── routes.py        # Endpoints REST e WebSocket
├── services/
│   └── authorization.py # Gerenciamento de notificações de votação
├── database.py          # Configuração do banco SQLite
├── main.py              # Aplicação FastAPI
├── models.py            # Modelos SQLModel
└── schemas.py           # Schemas Pydantic
```
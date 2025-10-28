from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from database import init_db

# Definindo o ciclo de vida da aplicação (substitui @app.on_event)
def lifespan(app: FastAPI):
    # Executado no startup
    init_db()
    yield
    # Executado no shutdown (se necessário)
    print("Aplicação finalizada")

app = FastAPI(
    title="Votação CIPA",
    version="1.0.0",
    lifespan=lifespan  # Novo padrão
)

# Middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclui as rotas principais
app.include_router(router, prefix="/api")

from __future__ import annotations

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router as api_router
from frontend.routes import router as frontend_router

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
app.include_router(api_router, prefix="/api")
app.include_router(frontend_router)

# Servir arquivos enviados (fotos)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

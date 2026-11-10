from contextlib import asynccontextmanager
import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import configuracoes
from app.core.observability import (
    configurar_logging,
    log_evento,
    request_id_context,
)
from app.db.session import motor, verificar_banco_vetorial
from app.api.chat import router as chat_router


@asynccontextmanager
async def ciclo_vida(app: FastAPI):
    yield
    await motor.dispose()


configurar_logging()
logger = logging.getLogger("multiagentes.http")

app = FastAPI(
    title="Multiagentes IA",
    description="API para orquestração de agentes de inteligência artificial.",
    version="0.1.0",
    lifespan=ciclo_vida,
)

# Inclusão correta do APIRouter
app.include_router(chat_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def inicio():
    return {
        "projeto": "multiagentes-ia",
        "mensagem": "API disponível",
    }


@app.get("/health")
async def health():
    try:
        await verificar_banco_vetorial()
        return {
            "status": "ok",
            "banco_vetorial": "conectado",
        }
    except Exception:
        return {
            "status": "degradado",
            "banco_vetorial": "indisponível",
        }
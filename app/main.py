import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routers import analisis, productos, proveedores, solicitudes
from app.schemas import ErrorRespuesta

app = FastAPI(
    title="API Agente de Compras",
    description="API de solo lectura para consultas y análisis del Agente de Compras",
    version="1.0.0",
    responses={503: {"model": ErrorRespuesta,
                     "description": "PostgreSQL no disponible o consulta fallida"}},
)
for router in (productos.router, proveedores.router, solicitudes.router, analisis.router):
    app.include_router(router)


@app.exception_handler(psycopg.Error)
def database_error(request: Request, exc: psycopg.Error):
    return JSONResponse(status_code=503, content={"detail": "No se pudo consultar PostgreSQL"})

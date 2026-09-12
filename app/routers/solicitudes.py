from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_database
from app.schemas import ErrorRespuesta, EstadoSolicitud, Solicitud
from app.services import compras_service as s

router = APIRouter(prefix="/solicitudes", tags=["solicitudes"])


@router.get('', response_model=list[Solicitud], operation_id='listar_solicitudes',
            summary='Consultar solicitudes de compra',
            description='Lista solicitudes ordenadas por código. Permite filtrar por pendiente, aprobada, rechazada o completada. Solo consulta; no cambia estados.')
def listar_solicitudes(estado: EstadoSolicitud | None = None, db: Connection = Depends(get_database)):
    return s.solicitudes(db, estado.value if estado else None)


@router.get('/pendientes', response_model=list[Solicitud], operation_id='listar_solicitudes_pendientes',
            summary='Obtener solicitudes pendientes',
            description='Devuelve únicamente solicitudes en estado pendiente, ordenadas por código de solicitud.')
def listar_solicitudes_pendientes(db: Connection = Depends(get_database)):
    return s.solicitudes(db, "pendiente")

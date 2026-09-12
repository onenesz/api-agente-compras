from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_database
from app.schemas import ErrorRespuesta, ProveedorProducto
from app.services import compras_service as s

router = APIRouter(prefix="/proveedores", tags=["proveedores"])


@router.get('/producto/{codigo_producto}', response_model=list[ProveedorProducto], operation_id='listar_proveedores_producto',
            summary='Consultar proveedores de un producto',
            description='Lista proveedores asociados al código exacto, ordenados por código de proveedor. Conserva precios y plazos null. Devuelve una lista vacía si no hay asociaciones o el producto no existe.')
def listar_proveedores_producto(codigo_producto: str, db: Connection = Depends(get_database)):
    return s.proveedores(db, codigo_producto)

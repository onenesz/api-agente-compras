from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_database
from app.schemas import ErrorRespuesta, Producto, Reposicion
from app.services import compras_service as s

router = APIRouter(prefix="/productos", tags=["productos"])


@router.get('', response_model=list[Producto], operation_id='listar_productos',
            summary='Obtener todos los productos',
            description='Consulta el catálogo completo con categoría y stocks. Conserva valores null. Ordenado por código de producto.')
def listar_productos(db: Connection = Depends(get_database)):
    return s.productos(db)


@router.get('/reposicion', response_model=list[Reposicion], operation_id='listar_reposicion',
            summary='Obtener productos que necesitan reposición',
            description='Devuelve productos con stock actual menor al mínimo y su déficit. Excluye mínimos null. Ordenado por código de producto.')
def listar_reposicion(db: Connection = Depends(get_database)):
    return s.reposicion(db)


@router.get('/{codigo_producto}', response_model=Producto, operation_id='obtener_producto',
            summary='Consultar un producto por código',
            description='Obtiene los datos y stocks de un producto exacto. Devuelve 404 si no existe.', responses={404: {"model": ErrorRespuesta, "description": "Producto no encontrado"}})
def obtener_producto(codigo_producto: str, db: Connection = Depends(get_database)):
    return s.producto(db, codigo_producto)

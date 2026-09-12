from fastapi import APIRouter, Depends
from psycopg import Connection

from app.database import get_database
from app.schemas import AnalisisProducto, DatoFaltante, ErrorRespuesta, Reposicion
from app.services import compras_service as s

router = APIRouter(prefix="/analisis", tags=["analisis"])


@router.get('/prioridades', response_model=list[Reposicion], operation_id='obtener_prioridades',
            summary='Obtener prioridades de reposición',
            description='Devuelve productos con stock actual menor al mínimo, excluyendo mínimos null. Ordena estrictamente por déficit DESC, stock actual ASC y código de producto ASC. Aplica desempates solo si empata el criterio anterior. No utiliza otras heurísticas.')
def obtener_prioridades(db: Connection = Depends(get_database)):
    return s.reposicion(db, prioridades=True)


@router.get('/datos-faltantes', response_model=list[DatoFaltante], operation_id='obtener_datos_faltantes',
            summary='Detectar información faltante para Compras',
            description='Identifica por tabla y claves cada stock mínimo, precio unitario o plazo de entrega null. Una entrada por campo faltante, sin completar datos. Ordena por tabla, producto, proveedor y campo.')
def obtener_datos_faltantes(db: Connection = Depends(get_database)):
    return s.datos_faltantes(db)


@router.get('/producto/{codigo_producto}', response_model=AnalisisProducto, operation_id='obtener_analisis_producto',
            summary='Analizar reposición y proveedores de un producto',
            description='Consolida producto, necesidad de reposición y proveedores asociados. Con mínimo null, necesidad y déficit son null. Sin reposición, necesidad es false y déficit null. Devuelve 404 si el producto no existe.', responses={404: {"model": ErrorRespuesta, "description": "Producto no encontrado"}})
def obtener_analisis_producto(codigo_producto: str, db: Connection = Depends(get_database)):
    return s.analisis_producto(db, codigo_producto)

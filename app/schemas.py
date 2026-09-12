from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class Producto(BaseModel):
    codigo_producto: str
    nombre: str
    categoria: str | None
    stock_actual: int
    stock_minimo: int | None


class Reposicion(BaseModel):
    codigo_producto: str
    nombre: str
    stock_actual: int
    stock_minimo: int
    deficit: int


class EstadoSolicitud(str, Enum):
    pendiente = "pendiente"
    aprobada = "aprobada"
    rechazada = "rechazada"
    completada = "completada"


class Solicitud(BaseModel):
    codigo_solicitud: str
    codigo_producto: str
    cantidad: int
    estado: EstadoSolicitud
    fecha_solicitud: date


class ProveedorProducto(BaseModel):
    codigo_proveedor: str
    nombre: str
    codigo_producto: str
    precio_unitario: Decimal | None = Field(description="Precio decimal exacto serializado como cadena; null si falta.")
    plazo_entrega_dias: int | None


class AnalisisProducto(BaseModel):
    producto: Producto
    necesita_reposicion: bool | None
    deficit: int | None = Field(description="Déficit positivo cuando necesita reposición; null en los demás casos.")
    proveedores_disponibles: list[ProveedorProducto]


class DatoFaltante(BaseModel):
    tabla: Literal["productos", "producto_proveedor"]
    codigo_producto: str
    codigo_proveedor: str | None
    campo: Literal["stock_minimo", "precio_unitario", "plazo_entrega_dias"]


class ErrorRespuesta(BaseModel):
    detail: str

from fastapi import HTTPException

PRODUCT_COLUMNS = "codigo_producto, nombre, categoria, stock_actual, stock_minimo"


def productos(db):
    return db.execute(f'SELECT {PRODUCT_COLUMNS} FROM public.productos ORDER BY codigo_producto COLLATE "C"').fetchall()


def producto(db, codigo):
    row = db.execute(f"SELECT {PRODUCT_COLUMNS} FROM public.productos WHERE codigo_producto = %s", (codigo,)).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return row


def reposicion(db, prioridades=False):
    order = 'deficit DESC, stock_actual ASC, codigo_producto COLLATE "C" ASC' if prioridades else 'codigo_producto COLLATE "C" ASC'
    return db.execute("SELECT codigo_producto, nombre, stock_actual, stock_minimo, "
                      "stock_minimo - stock_actual AS deficit FROM public.productos "
                      "WHERE stock_minimo IS NOT NULL AND stock_actual < stock_minimo "
                      f"ORDER BY {order}").fetchall()


def solicitudes(db, estado=None):
    query = "SELECT codigo_solicitud, codigo_producto, cantidad, estado, fecha_solicitud FROM public.solicitudes"
    params = ()
    if estado is not None:
        query += " WHERE estado = %s"
        params = (estado,)
    return db.execute(query + ' ORDER BY codigo_solicitud COLLATE "C"', params).fetchall()


def proveedores(db, codigo):
    return db.execute('SELECT p.codigo_proveedor, p.nombre, pp.codigo_producto, '
                      'pp.precio_unitario, pp.plazo_entrega_dias '
                      'FROM public.producto_proveedor pp JOIN public.proveedores p '
                      'ON p.codigo_proveedor = pp.codigo_proveedor '
                      'WHERE pp.codigo_producto = %s ORDER BY p.codigo_proveedor COLLATE "C"', (codigo,)).fetchall()


def analisis_producto(db, codigo):
    row = producto(db, codigo)
    necesita = None if row["stock_minimo"] is None else row["stock_actual"] < row["stock_minimo"]
    return dict(producto=row, necesita_reposicion=necesita,
                deficit=row["stock_minimo"] - row["stock_actual"] if necesita else None,
                proveedores_disponibles=proveedores(db, codigo))


def datos_faltantes(db):
    return db.execute("""
        SELECT * FROM (
            SELECT 'productos'::text AS tabla, codigo_producto,
                   NULL::text AS codigo_proveedor, 'stock_minimo'::text AS campo
            FROM public.productos WHERE stock_minimo IS NULL
            UNION ALL
            SELECT 'producto_proveedor', codigo_producto, codigo_proveedor, 'precio_unitario'
            FROM public.producto_proveedor WHERE precio_unitario IS NULL
            UNION ALL
            SELECT 'producto_proveedor', codigo_producto, codigo_proveedor, 'plazo_entrega_dias'
            FROM public.producto_proveedor WHERE plazo_entrega_dias IS NULL
        ) faltantes
        ORDER BY tabla COLLATE "C", codigo_producto COLLATE "C",
                 codigo_proveedor COLLATE "C" NULLS FIRST, campo COLLATE "C"
    """).fetchall()

from decimal import Decimal


def test_proveedores(client, data):
    names = {p['codigo_proveedor']: p['nombre'] for p in data['proveedores']}
    multiple = null_price = null_days = False
    for product in data['productos']:
        code = product['codigo_producto']
        expected = [dict(p, nombre=names[p['codigo_proveedor']]) for p in data['producto_proveedor'] if p['codigo_producto'] == code]
        response = client.get('/proveedores/producto/' + code)
        assert response.status_code == 200
        actual = response.json()
        for rows in (actual, expected):
            for p in rows:
                if p['precio_unitario'] is not None:
                    p['precio_unitario'] = Decimal(p['precio_unitario'])
        assert actual == sorted(expected, key=lambda p: p['codigo_proveedor'])
        multiple |= len(actual) > 1
        null_price |= any(p['precio_unitario'] is None for p in actual)
        null_days |= any(p['plazo_entrega_dias'] is None for p in actual)
    assert multiple and null_price and null_days
    assert client.get('/proveedores/producto/NO-EXISTE').json() == []
